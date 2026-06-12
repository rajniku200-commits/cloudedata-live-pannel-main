"""
routes/sessions.py
Active sessions dashboard API — list, kill, ping, stats.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from backend.models.server import Server
from backend.models.rdp_session import RdpSession
from backend.models.activity_log import ActivityLog
from backend.services.session_manager import SessionManager
from backend.services.guacamole_client import get_guac_client

sessions_bp = Blueprint('sessions', __name__, url_prefix='/api/sessions')
mgr = SessionManager()


@sessions_bp.route('/', methods=['GET'])
@login_required
def list_sessions():
    mgr.cleanup_stale_sessions()

    server_id = request.args.get('server_id', type=int)
    user_id = request.args.get('user_id', type=int)
    status = request.args.get('status', 'active')

    query = RdpSession.query
    if status != 'all':
        query = query.filter_by(status=status)
    if server_id is not None:
        query = query.filter_by(server_id=server_id)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    sessions = query.order_by(RdpSession.started_at.desc()).limit(200).all()
    return jsonify({'success': True, 'sessions': [s.to_dict() for s in sessions], 'count': len(sessions)}), 200


@sessions_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    return jsonify({'success': True, **mgr.get_stats()}), 200


@sessions_bp.route('/<int:session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    s = mgr.get_session(session_id)
    if not s:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    return jsonify({'success': True, 'session': s.to_dict()}), 200


@sessions_bp.route('/me', methods=['GET'])
@login_required
def my_sessions():
    sessions = mgr.get_user_sessions(current_user.id)
    return jsonify({'success': True, 'sessions': [s.to_dict() for s in sessions]}), 200


@sessions_bp.route('/launch', methods=['POST'])
@login_required
def launch_session():
    data = request.get_json(silent=True) or {}
    server_id = data.get('server_id')
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
        name=f'{server.name}-{current_user.id}',
        host=server.ip_address,
        port=getattr(server, 'rdp_port', 3389),
        rdp_username=getattr(server, 'rdp_username', ''),
        rdp_password=getattr(server, 'rdp_password', ''),
    )
    if not conn_result['success']:
        return jsonify({'success': False, 'error': conn_result['error']}), 500

    from flask import current_app
    token_result = guac.get_user_token(
        current_app.config.get('GUACAMOLE_USER', 'guacadmin'),
        current_app.config.get('GUACAMOLE_PASSWORD', 'guacadmin'),
    )
    if not token_result['success']:
        return jsonify({'success': False, 'error': token_result['error']}), 500

    connection_id = conn_result['connection_id']
    user_token = token_result['token']

    session = mgr.create_session(
        user_id=current_user.id,
        server_id=server.id,
        guac_token=user_token,
        guac_connection_id=connection_id,
        connection_type='rdp',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
    )

    ActivityLog.log(
        action='rdp_launch',
        category='rdp',
        user_id=current_user.id,
        server_id=server.id,
        session_id=session.id,
        ip_address=request.remote_addr,
    )

    client_url = guac.build_client_url(connection_id, user_token)
    return jsonify({'success': True, 'session_id': session.id, 'client_url': client_url, 'guac_token': user_token, 'connection_id': connection_id}), 201


@sessions_bp.route('/<int:session_id>/kill', methods=['DELETE', 'POST'])
@login_required
def kill_session(session_id):
    s = mgr.get_session(session_id)
    if not s:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    if s.guac_connection_id:
        try:
            guac = get_guac_client()
            guac.delete_connection(s.guac_connection_id)
        except Exception:
            pass

    result = mgr.close_session(session_id)
    ActivityLog.log(
        action='session_killed',
        category='rdp',
        user_id=current_user.id,
        session_id=session_id,
        ip_address=request.remote_addr,
    )
    return jsonify(result), 200


@sessions_bp.route('/<int:session_id>/ping', methods=['POST'])
@login_required
def ping_session(session_id):
    ok = mgr.ping_session(session_id)
    return jsonify({'success': ok}), 200 if ok else 404
