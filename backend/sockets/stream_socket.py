from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from backend.extensions import socketio
from backend.sockets.agent_socket import get_agent_sid
from backend.services.stream_manager import stream_manager


def register_socket_events(socketio_instance=None):
    return None


def _current_user_payload():
    if not current_user or not current_user.is_authenticated:
        return None
    return current_user.to_dict()


def can_view_stream(user, agent_id):
    return bool(user and user.is_authenticated and user.has_role('Admin', 'Manager', 'Viewer'))


def can_control_stream(user, agent_id, action):
    return bool(user and user.is_authenticated and user.has_role('Admin'))


def _permission_error(required_role='Admin'):
    return {'success': False, 'error': 'Forbidden', 'required_role': required_role}


def _emit_agent_command(agent_id, event, payload):
    agent_sid = get_agent_sid(agent_id)
    if not agent_sid:
        return False
    socketio.emit(event, payload, room=agent_sid, namespace='/agent')
    return True


@socketio.on('admin_start_agent_stream')
def admin_start_agent_stream(data):
    data = data or {}
    agent_id = data.get('agent_id')

    if not agent_id:
        emit('stream_control_result', {'success': False, 'error': 'agent_id required'})
        return
    if not can_control_stream(current_user, agent_id, 'start'):
        emit('stream_control_result', _permission_error('Admin'))
        return

    settings = stream_manager.configure_stream(agent_id, data.get('settings') or {})
    stream_manager.start_stream(agent_id, started_by=current_user.id)
    ok = _emit_agent_command(agent_id, 'start_stream', {'agent_id': agent_id, 'settings': settings})
    emit('stream_control_result', {
        'success': ok,
        'action': 'start',
        'agent_id': agent_id,
        'stream': stream_manager.status(agent_id),
        'error': None if ok else 'Agent is not connected',
    })


@socketio.on('admin_stop_agent_stream')
def admin_stop_agent_stream(data):
    data = data or {}
    agent_id = data.get('agent_id')

    if not agent_id:
        emit('stream_control_result', {'success': False, 'error': 'agent_id required'})
        return
    if not can_control_stream(current_user, agent_id, 'stop'):
        emit('stream_control_result', _permission_error('Admin'))
        return

    stream_manager.stop_stream(agent_id)
    ok = _emit_agent_command(agent_id, 'stop_stream', {'agent_id': agent_id})
    emit('stream_control_result', {
        'success': ok,
        'action': 'stop',
        'agent_id': agent_id,
        'stream': stream_manager.status(agent_id),
        'error': None if ok else 'Agent is not connected',
    })


@socketio.on('viewer_join_stream')
def viewer_join_stream(data):
    data = data or {}
    agent_id = data.get('agent_id')

    if not agent_id:
        emit('viewer_stream_result', {'success': False, 'error': 'agent_id required'})
        return
    if not can_view_stream(current_user, agent_id):
        emit('viewer_stream_result', _permission_error('Admin or Manager'))
        return

    room = stream_manager.room_name(agent_id)
    join_room(room)
    stream_manager.add_viewer(agent_id, request.sid, user_id=current_user.id)
    emit('viewer_stream_result', {
        'success': True,
        'action': 'join',
        'agent_id': agent_id,
        'room': room,
        'user': _current_user_payload(),
        'stream': stream_manager.status(agent_id),
    })

    frame = stream_manager.get_frame(agent_id)
    if frame:
        emit('screen_update', {'agent_id': agent_id, 'frame': frame})


@socketio.on('viewer_leave_stream')
def viewer_leave_stream(data):
    data = data or {}
    agent_id = data.get('agent_id')
    if agent_id:
        leave_room(stream_manager.room_name(agent_id))
    removed = stream_manager.remove_viewer(request.sid)
    emit('viewer_stream_result', {'success': True, 'action': 'leave', 'agent_ids': removed})


@socketio.on('stream_status')
def stream_status(data=None):
    data = data or {}
    agent_id = data.get('agent_id')
    if not can_view_stream(current_user, agent_id):
        emit('stream_status_result', _permission_error('Admin or Manager'))
        return
    emit('stream_status_result', {'success': True, 'streams': stream_manager.status(agent_id)})


@socketio.on('viewer_mouse_event')
def viewer_mouse_event(data):
    data = data or {}
    agent_id = data.get('agent_id')
    if not can_control_stream(current_user, agent_id, 'mouse'):
        emit('input_control_result', _permission_error('Admin'))
        return
    ok = _emit_agent_command(agent_id, 'mouse_event', data)
    emit('input_control_result', {'success': ok, 'type': 'mouse', 'agent_id': agent_id})


@socketio.on('viewer_keyboard_event')
def viewer_keyboard_event(data):
    data = data or {}
    agent_id = data.get('agent_id')
    if not can_control_stream(current_user, agent_id, 'keyboard'):
        emit('input_control_result', _permission_error('Admin'))
        return
    ok = _emit_agent_command(agent_id, 'keyboard_event', data)
    emit('input_control_result', {'success': ok, 'type': 'keyboard', 'agent_id': agent_id})


@socketio.on('disconnect')
def viewer_disconnect():
    stream_manager.remove_viewer(request.sid)


@socketio.on('screen_frame', namespace='/agent')
def handle_screen_frame(data):
    data = data or {}
    agent_id = data.get('agent_id')
    frame = data.get('frame')

    if not agent_id or not frame:
        return

    stream = stream_manager.update_frame(agent_id, request.sid, frame)
    socketio.emit(
        'screen_update',
        {'agent_id': agent_id, 'frame': stream.get('last_frame')},
        room=stream_manager.room_name(agent_id),
        namespace='/',
    )


@socketio.on('screen_error', namespace='/agent')
def handle_screen_error(data):
    data = data or {}
    agent_id = data.get('agent_id')
    socketio.emit(
        'screen_error',
        {'agent_id': agent_id, 'error': data.get('error')},
        room=stream_manager.room_name(agent_id),
        namespace='/',
    )


@socketio.on('mouse_event_result', namespace='/agent')
def handle_mouse_event_result(data):
    data = data or {}
    socketio.emit(
        'input_control_result',
        {'type': 'mouse', **data},
        room=stream_manager.room_name(data.get('agent_id')),
        namespace='/',
    )


@socketio.on('keyboard_event_result', namespace='/agent')
def handle_keyboard_event_result(data):
    data = data or {}
    socketio.emit(
        'input_control_result',
        {'type': 'keyboard', **data},
        room=stream_manager.room_name(data.get('agent_id')),
        namespace='/',
    )
