import re
import os
from datetime import datetime
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from backend.extensions import db
from backend.models.activity_log import ActivityLog
from backend.models.published_app import ApplicationAssignment, PublishedApp
from backend.models.rdp_session import RdpSession
from backend.models.server import Server
from backend.models.user import User
from backend.routes.auth import admin_required

apps_bp = Blueprint('apps', __name__, url_prefix='/api/apps')


def _slugify(value):
    slug = re.sub(r'[^a-z0-9]+', '-', (value or '').strip().lower()).strip('-')
    return slug or 'app'


def _payload():
    return request.get_json(silent=True) or request.form.to_dict()


def _as_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


@apps_bp.route('', methods=['GET'])
@admin_required
def list_apps():
    apps = PublishedApp.query.order_by(PublishedApp.name.asc()).all()
    data = []
    for app in apps:
        item = app.to_dict()
        item['assigned_user_ids'] = [
            assignment.user_id
            for assignment in app.assignments.filter_by(is_enabled=True).all()
        ]
        data.append(item)
    return jsonify({'success': True, 'apps': data}), 200


@apps_bp.route('', methods=['POST'])
@admin_required
def create_app():
    data = _payload()
    required = ['server_id', 'name']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'success': False, 'error': 'Missing required fields', 'missing': missing}), 400

    server = Server.get_by_id(data.get('server_id'))
    if not server:
        return jsonify({'success': False, 'error': 'Server not found'}), 404

    launch_mode = data.get('launch_mode') or 'remote_app'
    if launch_mode not in ('remote_app', 'initial_program', 'desktop'):
        return jsonify({'success': False, 'error': 'Invalid launch_mode'}), 400
    validation_error = _validate_app_target(launch_mode, data)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400

    slug = data.get('slug') or _slugify(data.get('name'))
    if PublishedApp.query.filter_by(slug=slug).first():
        return jsonify({'success': False, 'error': 'App slug already exists'}), 409

    app = PublishedApp(
        server_id=server.id,
        name=data.get('name').strip(),
        slug=slug,
        icon=data.get('icon') or 'app',
        launch_mode=launch_mode,
        remote_app_program=data.get('remote_app_program'),
        initial_program=data.get('initial_program'),
        working_directory=data.get('working_directory'),
        arguments=data.get('arguments'),
        description=data.get('description'),
        is_active=_as_bool(data.get('is_active'), True),
    ).save()
    ActivityLog.log(current_user.id, f'app_created #{app.id}', 'software', server_id=server.id, ip_address=request.remote_addr)
    return jsonify({'success': True, 'app': app.to_dict()}), 201


@apps_bp.route('/<int:app_id>', methods=['PATCH', 'POST'])
@admin_required
def update_app(app_id):
    app = PublishedApp.get_by_id(app_id)
    if not app:
        return jsonify({'success': False, 'error': 'App not found'}), 404

    data = _payload()
    launch_mode = data.get('launch_mode') or app.launch_mode
    validation_error = _validate_app_target(launch_mode, data, existing_app=app)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400
    for field in (
        'name',
        'icon',
        'launch_mode',
        'remote_app_program',
        'initial_program',
        'working_directory',
        'arguments',
        'description',
        'is_active',
    ):
        if field in data:
            value = _as_bool(data.get(field), True) if field == 'is_active' else data.get(field)
            setattr(app, field, value)
    if 'server_id' in data:
        server = Server.get_by_id(data.get('server_id'))
        if not server:
            return jsonify({'success': False, 'error': 'Server not found'}), 404
        app.server_id = server.id
    db.session.commit()
    ActivityLog.log(current_user.id, f'app_updated #{app.id}', 'software', server_id=app.server_id, ip_address=request.remote_addr)
    return jsonify({'success': True, 'app': app.to_dict()}), 200


@apps_bp.route('/<int:app_id>', methods=['DELETE'])
@admin_required
def delete_app(app_id):
    app = PublishedApp.get_by_id(app_id)
    if not app:
        return jsonify({'success': False, 'error': 'App not found'}), 404
    RdpSession.query.filter_by(published_app_id=app.id).update({'published_app_id': None}, synchronize_session=False)
    db.session.delete(app)
    db.session.commit()
    ActivityLog.log(current_user.id, f'app_deleted #{app_id}', 'software', ip_address=request.remote_addr)
    return jsonify({'success': True, 'message': 'Software deleted'}), 200


@apps_bp.route('/<int:app_id>/assign', methods=['POST'])
@admin_required
def assign_app(app_id):
    app = PublishedApp.get_by_id(app_id)
    if not app:
        return jsonify({'success': False, 'error': 'App not found'}), 404

    data = _payload()
    user = User.get_by_id(data.get('user_id'))
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    assignment = ApplicationAssignment.find(user.id, app.id)
    if assignment:
        assignment.is_enabled = _as_bool(data.get('is_enabled'), True)
    else:
        assignment = ApplicationAssignment(
            user_id=user.id,
            app_id=app.id,
            is_enabled=_as_bool(data.get('is_enabled'), True),
        )
        db.session.add(assignment)
    db.session.commit()
    ActivityLog.log(current_user.id, f'app_assigned app#{app.id} user#{user.id}', 'assignment', ip_address=request.remote_addr)
    return jsonify({'success': True, 'assignment': assignment.to_dict()}), 200


@apps_bp.route('/assignments/user/<int:user_id>', methods=['GET'])
@admin_required
def user_assignments(user_id):
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    assignments = ApplicationAssignment.query.filter_by(user_id=user.id, is_enabled=True).all()
    assigned_ids = [assignment.app_id for assignment in assignments]
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'assigned_app_ids': assigned_ids,
        'assignments': [assignment.to_dict() for assignment in assignments],
        'available_apps': [app.to_dict() for app in PublishedApp.query.order_by(PublishedApp.name.asc()).all()],
    }), 200


@apps_bp.route('/assignments/bulk', methods=['POST'])
@admin_required
def bulk_assign_apps():
    data = _payload()
    user_ids = [int(item) for item in data.get('user_ids', []) if str(item).isdigit()]
    app_ids = [int(item) for item in data.get('app_ids', []) if str(item).isdigit()]
    enabled = _as_bool(data.get('is_enabled'), True)
    changed = 0
    for user_id in user_ids:
        if not User.get_by_id(user_id):
            continue
        for app_id in app_ids:
            if not PublishedApp.get_by_id(app_id):
                continue
            assignment = ApplicationAssignment.find(user_id, app_id)
            if assignment:
                assignment.is_enabled = enabled
            else:
                db.session.add(ApplicationAssignment(user_id=user_id, app_id=app_id, is_enabled=enabled))
            changed += 1
    db.session.commit()
    ActivityLog.log(current_user.id, f'app_bulk_assignment {changed}', 'assignment', ip_address=request.remote_addr)
    return jsonify({'success': True, 'message': f'{changed} assignments updated', 'changed': changed}), 200


@apps_bp.route('/upload', methods=['POST'])
@admin_required
def upload_software():
    uploaded = request.files.get('file')
    if not uploaded:
        return jsonify({'success': False, 'error': 'file is required'}), 400
    filename = os.path.basename(uploaded.filename or '')
    if not filename.lower().endswith(('.exe', '.msi', '.bat', '.cmd')):
        return jsonify({'success': False, 'error': 'Only executable installer files are allowed'}), 400
    upload_dir = os.path.join(current_app.instance_path, 'software_uploads')
    os.makedirs(upload_dir, exist_ok=True)
    stored_name = f'{datetime.utcnow().strftime("%Y%m%d%H%M%S")}-{uuid4().hex[:8]}-{filename}'
    path = os.path.join(upload_dir, stored_name)
    uploaded.save(path)
    ActivityLog.log(current_user.id, f'software_uploaded {filename}', 'software', ip_address=request.remote_addr)
    return jsonify({'success': True, 'file': {'name': stored_name, 'path': path, 'size': os.path.getsize(path)}}), 201


@apps_bp.route('/<int:app_id>/assign/<int:user_id>', methods=['DELETE'])
@admin_required
def unassign_app(app_id, user_id):
    assignment = ApplicationAssignment.find(user_id, app_id)
    if not assignment:
        return jsonify({'success': False, 'error': 'Assignment not found'}), 404
    db.session.delete(assignment)
    db.session.commit()
    ActivityLog.log(current_user.id, f'app_unassigned app#{app_id} user#{user_id}', 'assignment', ip_address=request.remote_addr)
    return jsonify({'success': True}), 200


def _validate_app_target(launch_mode, data, existing_app=None):
    remote_app_program = data.get('remote_app_program')
    initial_program = data.get('initial_program')
    if existing_app:
        remote_app_program = remote_app_program if remote_app_program is not None else existing_app.remote_app_program
        initial_program = initial_program if initial_program is not None else existing_app.initial_program
    if launch_mode == 'remote_app':
        if not remote_app_program:
            return 'RemoteApp program is required'
        if not str(remote_app_program).startswith('||') and not _looks_like_windows_path(remote_app_program):
            return 'RemoteApp program must be a RemoteApp alias like ||Tally or a Windows executable path'
    if launch_mode == 'initial_program' and not initial_program:
        return 'Initial program is required'
    return None


def _looks_like_windows_path(value):
    return bool(re.match(r'^[a-zA-Z]:\\.+', str(value or '')))
