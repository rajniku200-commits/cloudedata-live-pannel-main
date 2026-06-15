import re

from flask import Blueprint, jsonify, request
from flask_login import login_required

from backend.extensions import db
from backend.models.published_app import ApplicationAssignment, PublishedApp
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
    return jsonify({'success': True, 'app': app.to_dict()}), 201


@apps_bp.route('/<int:app_id>', methods=['PATCH'])
@admin_required
def update_app(app_id):
    app = PublishedApp.get_by_id(app_id)
    if not app:
        return jsonify({'success': False, 'error': 'App not found'}), 404

    data = _payload()
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
    return jsonify({'success': True, 'app': app.to_dict()}), 200


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
    return jsonify({'success': True, 'assignment': assignment.to_dict()}), 200


@apps_bp.route('/<int:app_id>/assign/<int:user_id>', methods=['DELETE'])
@admin_required
def unassign_app(app_id, user_id):
    assignment = ApplicationAssignment.find(user_id, app_id)
    if not assignment:
        return jsonify({'success': False, 'error': 'Assignment not found'}), 404
    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'success': True}), 200
