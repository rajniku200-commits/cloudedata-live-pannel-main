import os
import threading
import time

import socketio

try:
    from agent.keyboard_control import KeyboardControl
    from agent.mouse_control import MouseControl
    from agent.screen_agent import ScreenAgent
    from agent.system_info import get_system_info
except ImportError:
    from keyboard_control import KeyboardControl
    from mouse_control import MouseControl
    from screen_agent import ScreenAgent
    from system_info import get_system_info


SERVER_URL = os.getenv('LIVEPANEL_SERVER_URL', 'http://localhost:5000')
NAMESPACE = '/agent'

sio = socketio.Client()
system_info = get_system_info()
agent_id = system_info['agent_id']
screen_stream = ScreenAgent(sio, agent_id)
mouse_control = MouseControl()
keyboard_control = KeyboardControl()


@sio.event(namespace=NAMESPACE)
def connect():
    print('[+] Connected to LivePanel Server')
    sio.emit('agent_connect', system_info, namespace=NAMESPACE)
    threading.Thread(target=heartbeat, daemon=True).start()


@sio.event(namespace=NAMESPACE)
def disconnect():
    print('[-] Disconnected from Server')
    screen_stream.stop()


@sio.on('start_stream', namespace=NAMESPACE)
def start_stream(data):
    data = data or {}
    if data.get('agent_id') in (None, agent_id):
        screen_stream.start()


@sio.on('stop_stream', namespace=NAMESPACE)
def stop_stream(data):
    data = data or {}
    if data.get('agent_id') in (None, agent_id):
        screen_stream.stop()


@sio.on('mouse_event', namespace=NAMESPACE)
def mouse_event(data):
    result = mouse_control.handle_event(data)
    sio.emit('mouse_event_result', {'agent_id': agent_id, **result}, namespace=NAMESPACE)


@sio.on('keyboard_event', namespace=NAMESPACE)
def keyboard_event(data):
    result = keyboard_control.handle_event(data)
    sio.emit('keyboard_event_result', {'agent_id': agent_id, **result}, namespace=NAMESPACE)


def heartbeat():
    while sio.connected:
        sio.emit('heartbeat', {'agent_id': agent_id}, namespace=NAMESPACE)
        time.sleep(5)


def start_agent():
    while True:
        try:
            sio.connect(SERVER_URL, namespaces=[NAMESPACE])
            sio.wait()
        except Exception as error:
            print('[ERROR]', error)
            print('Reconnecting in 5 seconds...')
            time.sleep(5)


if __name__ == '__main__':
    start_agent()
