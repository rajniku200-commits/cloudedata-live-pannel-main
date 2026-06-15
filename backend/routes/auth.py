import hmac
from datetime import datetime

from flask import Blueprint, request, jsonify, redirect, render_template, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_user, logout_user, login_required
from functools import wraps

from backend.models.user import User
from backend.models.login_link import LoginLink
from backend.models.published_app import ApplicationAssignment
from backend.models.rdp_session import RdpSession
from backend.extensions import db
from backend.models.activity_log import ActivityLog
from backend.services.two_factor import verify_totp

auth = Blueprint('auth', __name__)


def _get_request_data():
    return request.get_json(silent=True) or request.form


def _password_matches(user, password):
    stored = user.password or ''
    is_hash = stored.startswith(('scrypt:', 'pbkdf2:', 'argon2:'))
    if is_hash and check_password_hash(stored, password):
        return True
    if not is_hash and hmac.compare_digest(stored, password):
        user.password = generate_password_hash(password)
        ActivityLog.log(user.id, 'password_hash_migrated', 'auth', ip_address=request.remote_addr)
        return True
    return False


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user.has_role(*roles):
                return jsonify({'message': 'Forbidden', 'required_roles': list(roles)}), 403
            return view(*args, **kwargs)

        return wrapped
    return decorator


admin_required = role_required('Admin')


@auth.route('/register', methods=['POST'])
def register():
    data = _get_request_data()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    if User.find_by_username(username):
        return jsonify({'message': 'Username already exists'}), 409

    role = 'Admin' if User.query.count() == 0 else 'User'
    user = User(username=username, password=generate_password_hash(password), role=role).save()
    return jsonify({'message': 'User registered successfully', **user.to_dict()}), 201


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('index.html')

    data = _get_request_data()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = User.find_by_username(username)
    if user and not user.is_active:
        ActivityLog.log(user.id, 'login_blocked_inactive', 'auth', ip_address=request.remote_addr)
        return jsonify({'message': 'User account is inactive'}), 403

    if user and _password_matches(user, password):
        if user.two_factor_enabled:
            token = data.get('token') or data.get('two_factor_code')
            if not token:
                return jsonify({'message': 'Two-factor code required', 'requires_2fa': True}), 401
            if not verify_totp(user.two_factor_secret, token):
                ActivityLog.log(user.id, 'login_2fa_failed', 'auth', ip_address=request.remote_addr)
                return jsonify({'message': 'Invalid two-factor code', 'requires_2fa': True}), 401
        login_user(user)
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        ActivityLog.log(user.id, 'login_success', 'auth', ip_address=request.remote_addr)
        return jsonify({'message': 'Login successful', 'redirect': url_for('portal.portal_home'), 'user': user.to_dict()}), 200

    return jsonify({'message': 'Invalid credentials'}), 401


@auth.route('/login-link/<token>', methods=['GET'])
def login_link(token):
    link = LoginLink.query.filter_by(token=token).first()
    if not link or not link.is_valid or not link.user or not link.user.is_active:
        return jsonify({'message': 'Login link is invalid, expired, revoked, or already used'}), 403
    link.used_at = datetime.utcnow()
    link.user.last_login_at = datetime.utcnow()
    db.session.commit()
    login_user(link.user)
    ActivityLog.log(link.user.id, f'login_link_used #{link.id}', 'auth', ip_address=request.remote_addr)
    return redirect(url_for('portal.portal_home'))


@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    if request.method == 'GET':
        return redirect(url_for('auth.login'))
    return jsonify({'message': 'Logged out successfully'}), 200


@auth.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify({'user': current_user.to_dict()}), 200


@auth.route('/users', methods=['GET'])
@admin_required
def users():
    query = User.query
    search = (request.args.get('search') or '').strip()
    status = (request.args.get('status') or 'all').strip().lower()
    role = (request.args.get('role') or '').strip()
    if search:
        query = query.filter(User.username.ilike(f'%{search}%'))
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    if role:
        try:
            query = query.filter_by(role=User.normalize_role(role))
        except ValueError:
            return jsonify({'users': []}), 200
    return jsonify({'users': [user.to_dict() for user in query.order_by(User.id.asc()).all()]}), 200


@auth.route('/users', methods=['POST'])
@admin_required
def create_user():
    data = _get_request_data()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    role = data.get('role') or 'User'

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400
    if User.find_by_username(username):
        return jsonify({'message': 'Username already exists'}), 409

    try:
        role = User.normalize_role(role)
    except ValueError as error:
        return jsonify({'message': str(error)}), 400

    user = User(username=username, password=generate_password_hash(password), role=role).save()
    ActivityLog.log(current_user.id, f'user_created #{user.id}', 'user', ip_address=request.remote_addr)
    return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201


@auth.route('/users/<int:user_id>', methods=['PATCH', 'POST'])
@admin_required
def update_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = _get_request_data()
    username = (data.get('username') or user.username).strip()
    if username != user.username and User.find_by_username(username):
        return jsonify({'message': 'Username already exists'}), 409
    user.username = username
    if data.get('password'):
        user.password = generate_password_hash((data.get('password') or '').strip())
    if 'role' in data:
        try:
            user.set_role(data.get('role'))
        except ValueError as error:
            return jsonify({'message': str(error)}), 400
    if 'is_active' in data:
        user.is_active = str(data.get('is_active')).strip().lower() in ('1', 'true', 'yes', 'on')
    db.session.commit()
    ActivityLog.log(current_user.id, f'user_updated #{user.id}', 'user', ip_address=request.remote_addr)
    return jsonify({'message': 'User updated', 'user': user.to_dict()}), 200


@auth.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    if user.id == current_user.id:
        return jsonify({'message': 'You cannot delete your own account'}), 400
    ApplicationAssignment.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    LoginLink.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    RdpSession.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()
    ActivityLog.log(current_user.id, f'user_deleted #{user_id}', 'user', ip_address=request.remote_addr)
    return jsonify({'message': 'User deleted'}), 200


@auth.route('/users/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_users():
    data = _get_request_data()
    ids = [int(item) for item in data.get('user_ids', []) if str(item).isdigit()]
    ids = [item for item in ids if item != current_user.id]
    ApplicationAssignment.query.filter(ApplicationAssignment.user_id.in_(ids)).delete(synchronize_session=False)
    LoginLink.query.filter(LoginLink.user_id.in_(ids)).delete(synchronize_session=False)
    RdpSession.query.filter(RdpSession.user_id.in_(ids)).delete(synchronize_session=False)
    deleted = User.query.filter(User.id.in_(ids)).delete(synchronize_session=False) if ids else 0
    db.session.commit()
    ActivityLog.log(current_user.id, f'users_bulk_deleted {deleted}', 'user', ip_address=request.remote_addr)
    return jsonify({'message': f'{deleted} users deleted', 'deleted': deleted}), 200


@auth.route('/users/import-csv', methods=['POST'])
@admin_required
def import_users_csv():
    import csv
    import io

    uploaded = request.files.get('file')
    if not uploaded:
        return jsonify({'message': 'CSV file is required'}), 400
    text = uploaded.read().decode('utf-8-sig')
    rows = csv.DictReader(io.StringIO(text))
    created = 0
    skipped = []
    for index, row in enumerate(rows, start=2):
        username = (row.get('username') or '').strip()
        password = (row.get('password') or '').strip()
        role = row.get('role') or 'User'
        if not username or not password or User.find_by_username(username):
            skipped.append(index)
            continue
        try:
            role = User.normalize_role(role)
        except ValueError:
            skipped.append(index)
            continue
        db.session.add(User(username=username, password=generate_password_hash(password), role=role))
        created += 1
    db.session.commit()
    ActivityLog.log(current_user.id, f'users_csv_imported {created}', 'user', ip_address=request.remote_addr)
    return jsonify({'message': f'{created} users imported', 'created': created, 'skipped_rows': skipped}), 201


@auth.route('/users/<int:user_id>/role', methods=['PATCH', 'POST'])
@admin_required
def update_user_role(user_id):
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = _get_request_data()
    try:
        user.set_role(data.get('role'))
    except ValueError as error:
        return jsonify({'message': str(error)}), 400

    db.session.commit()
    ActivityLog.log(current_user.id, f'user_role_updated #{user.id}', 'user', ip_address=request.remote_addr)
    return jsonify({'message': 'Role updated', 'user': user.to_dict()}), 200
