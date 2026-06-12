from flask_socketio import emit
from backend.extensions import socketio

def register_sockets():
    from backend.sockets import agent_socket
    from backend.sockets import stream_socket
    agent_socket.register_socket_events(socketio)
    stream_socket.register_socket_events(socketio)

def register_socket_events(socketio):

    @socketio.on('connect')
    def connect():

        print("Client Connected")

        emit(
            'message',
            {'data': 'Connected'}
        )
    @socketio.on('terminal_command')
    def handle_terminal_command(data):

        command = data.get('command')
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        emit(
            'terminal_output',
            {'output': result.stdout, 'error': result.stderr}
        )
