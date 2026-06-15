from flask import Blueprint, request, jsonify, redirect, render_template, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_user, logout_user, login_required
from functools import wraps

from backend.models.user import User
from backend.extensions import db
from backend.models.activity_log import ActivityLog
from backend.services.two_factor import verify_totp

auth = Blueprint('auth', __name__)


def _get_request_data():
    return request.get_json(silent=True) or request.form


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
    if user and check_password_hash(user.password, password):
        if user.two_factor_enabled:
            token = data.get('token') or data.get('two_factor_code')
            if not token:
                return jsonify({'message': 'Two-factor code required', 'requires_2fa': True}), 401
            if not verify_totp(user.two_factor_secret, token):
                ActivityLog.log(user.id, 'login_2fa_failed', 'auth', ip_address=request.remote_addr)
                return jsonify({'message': 'Invalid two-factor code', 'requires_2fa': True}), 401
        login_user(user)
        ActivityLog.log(user.id, 'login_success', 'auth', ip_address=request.remote_addr)
        return jsonify({'message': 'Login successful', 'redirect': url_for('portal.portal_home'), 'user': user.to_dict()}), 200

    return jsonify({'message': 'Invalid credentials'}), 401


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
    return jsonify({'users': [user.to_dict() for user in User.query.order_by(User.id.asc()).all()]}), 200


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
    return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201


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
    return jsonify({'message': 'Role updated', 'user': user.to_dict()}), 200
