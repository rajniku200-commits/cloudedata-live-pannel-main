"""
routes/portal.py
User portal — serves login page, app launcher, and RDP launch endpoint.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from backend.models.server import Server
from backend.models.rdp_session import RdpSession
from backend.models.activity_log import ActivityLog
from backend.models.published_app import ApplicationAssignment, PublishedApp
from backend.routes.auth import admin_required
from backend.services.session_manager import SessionManager
from backend.services.guacamole_client import get_guac_client

portal_bp = Blueprint('portal', __name__, url_prefix='/portal')
mgr = SessionManager()


@portal_bp.route('/', methods=['GET'])
@login_required
def portal_home():
    servers = Server.query.filter_by(is_active=True).all()
    return render_template('portal.html', user=current_user, servers=[s.to_dict() for s in servers])


@portal_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard():
    mgr.cleanup_stale_sessions()
    stats = mgr.get_stats()
    servers = Server.query.all()
    return render_template('dashboard.html', user=current_user, stats=stats, servers=[s.to_dict() for s in servers])


@portal_bp.route('/api/servers', methods=['GET'])
@login_required
def get_portal_servers():
    servers = Server.query.filter_by(is_active=True).all()
    return jsonify({'success': True, 'servers': [s.to_dict() for s in servers]}), 200


@portal_bp.route('/api/apps', methods=['GET'])
@login_required
def get_portal_apps():
    apps = PublishedApp.assigned_to_user(current_user.id)
    return jsonify({'success': True, 'apps': [app.to_dict() for app in apps]}), 200


@portal_bp.route('/api/apps/<int:app_id>/launch', methods=['POST'])
@login_required
def portal_launch_app(app_id):
    app = PublishedApp.get_by_id(app_id)
    if not app or not app.is_active:
        return jsonify({'success': False, 'error': 'Application not found'}), 404

    assignment = ApplicationAssignment.find(current_user.id, app.id)
    if not assignment or not assignment.is_enabled:
        return jsonify({'success': False, 'error': 'Application is not assigned to this user'}), 403

    server = app.server
    if not server or not server.is_active:
        return jsonify({'success': False, 'error': 'Application server is offline'}), 409

    guac = get_guac_client()
    conn_result = guac.create_rdp_connection(
        name=f'{app.slug}-u{current_user.id}',
        host=server.ip_address,
        port=getattr(server, 'rdp_port', 3389),
        rdp_username=getattr(server, 'rdp_username', ''),
        rdp_password=getattr(server, 'rdp_password', ''),
        app=app.to_dict(include_server=False),
    )
    if not conn_result['success']:
        return jsonify({'success': False, 'error': conn_result.get('error')}), 500

    from flask import current_app
    token_result = guac.get_user_token(
        current_app.config.get('GUACAMOLE_USER', 'guacadmin'),
        current_app.config.get('GUACAMOLE_PASSWORD', 'guacadmin'),
    )
    if not token_result['success']:
        return jsonify({'success': False, 'error': token_result.get('error')}), 500

    connection_id = conn_result['connection_id']
    user_token = token_result['token']

    session = mgr.create_session(
        user_id=current_user.id,
        server_id=server.id,
        published_app_id=app.id,
        guac_token=user_token,
        guac_connection_id=connection_id,
        connection_type='app',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
    )

    ActivityLog.log(
        action='app_launch',
        category='remote_app',
        user_id=current_user.id,
        server_id=server.id,
        session_id=session.id,
        ip_address=request.remote_addr,
    )

    client_url = guac.build_client_url(connection_id, user_token)
    return jsonify({
        'success': True,
        'session_id': session.id,
        'client_url': client_url,
        'app': app.to_dict(),
    }), 201


@portal_bp.route('/api/launch', methods=['POST'])
@login_required
def portal_launch():
    data = request.get_json(silent=True) or {}
    server_id = data.get('server_id')
    conn_type = data.get('connection_type', 'rdp')

    if server_id is None:
        return jsonify({'success': False, 'error': 'server_id required'}), 400

    try:
        server_id = int(server_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'server_id must be a number'}), 400

    server = Server.query.get(server_id)
    if not server:
        return jsonify({'success': False, 'error': 'Server not found'}), 404

    guac = get_guac_client()
    conn_result = guac.create_rdp_connection(
        name=f'{server.name}-u{current_user.id}',
        host=server.ip_address,
        port=getattr(server, 'rdp_port', 3389),
        rdp_username=getattr(server, 'rdp_username', ''),
        rdp_password=getattr(server, 'rdp_password', ''),
    )
    if not conn_result['success']:
        return jsonify({'success': False, 'error': conn_result.get('error')}), 500

    from flask import current_app
    token_result = guac.get_user_token(
        current_app.config.get('GUACAMOLE_USER', 'guacadmin'),
        current_app.config.get('GUACAMOLE_PASSWORD', 'guacadmin'),
    )
    if not token_result['success']:
        return jsonify({'success': False, 'error': token_result.get('error')}), 500

    connection_id = conn_result['connection_id']
    user_token = token_result['token']

    session = mgr.create_session(
        user_id=current_user.id,
        server_id=server.id,
        guac_token=user_token,
        guac_connection_id=connection_id,
        connection_type=conn_type,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
    )

    ActivityLog.log(
        action=f'{conn_type}_launch',
        category=conn_type,
        user_id=current_user.id,
        server_id=server.id,
        session_id=session.id,
        ip_address=request.remote_addr,
    )

    client_url = guac.build_client_url(connection_id, user_token)
    return jsonify({'success': True, 'session_id': session.id, 'client_url': client_url}), 201


@portal_bp.route('/api/my-sessions', methods=['GET'])
@login_required
def my_sessions():
    sessions = mgr.get_user_sessions(current_user.id)
    return jsonify({'success': True, 'sessions': [s.to_dict() for s in sessions]}), 200


@portal_bp.route('/api/sessions/stats', methods=['GET'])
@login_required
def sessions_stats():
    active_count = RdpSession.query.filter_by(user_id=current_user.id, status='active').count()
    total_count = RdpSession.query.filter_by(user_id=current_user.id).count()
    return jsonify({'success': True, 'active': active_count, 'total': total_count}), 200
