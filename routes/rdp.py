from flask import current_app
from flask_socketio import Namespace, emit, join_room, leave_room
from services.rdp_manager import RDPManager

rdp_manager = RDPManager()

class RDPNamespace(Namespace):
    def on_connect(self):
        sid = getattr(current_app, 'request', None)
        emit('connected', {'message': 'RDP gateway connected'})

    def on_disconnect(self):
        # client disconnected
        pass

    def on_rdp_connect(self, data):
        """Client requests to start an RDP session.
        data: {"host":..., "port":..., "username":..., "password":..., "options": {...}}
        """
        try:
            session_id = rdp_manager.create_session(data)
            join_room(session_id)
            emit('rdp_connected', {'session_id': session_id})
        except Exception as e:
            emit('rdp_error', {'error': str(e)})

    def on_rdp_input(self, data):
        """Forward input events (mouse/keyboard) to backend RDP session."""
        session_id = data.get('session_id')
        event = data.get('event')
        try:
            rdp_manager.send_input(session_id, event)
        except Exception as e:
            emit('rdp_error', {'error': str(e)})

    def on_rdp_resize(self, data):
        session_id = data.get('session_id')
        width = data.get('width')
        height = data.get('height')
        try:
            rdp_manager.resize(session_id, width, height)
        except Exception as e:
            emit('rdp_error', {'error': str(e)})

    def on_rdp_disconnect(self, data):
        session_id = data.get('session_id')
        try:
            rdp_manager.close_session(session_id)
            leave_room(session_id)
            emit('rdp_disconnected', {'session_id': session_id})
        except Exception as e:
            emit('rdp_error', {'error': str(e)})


def init_rdp_namespace(socketio):
    socketio.on_namespace(RDPNamespace('/rdp'))
