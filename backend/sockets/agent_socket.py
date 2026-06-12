from flask import request
from backend.extensions import socketio
from backend.services.agent_manager import register_agent, set_offline, update_heartbeat
from backend.services.stream_manager import remove_sid

connected_agents = {}


def get_agent_sid(agent_id):
    for sid, info in connected_agents.items():
        if info.get("agent_id") == agent_id:
            return sid
    return None


def register_socket_events(socketio_instance=None):
    """Import hook used by sockets.socket_handler.

    The event handlers in this module are registered by the decorators below
    when the module is imported.
    """
    return None

@socketio.on("agent_connect", namespace='/agent')
def handle_agent_connect(data):
    data = data or {}
    agent_id = data.get("agent_id")
    if agent_id:
        register_agent(
            agent_id=agent_id,
            hostname=data.get("hostname"),
            ip_address=data.get("ip_address"),
            username=data.get("username"),
            os=data.get("os"),
            cpu=data.get("cpu"),
            ram=data.get("ram")
        )
        connected_agents[request.sid] = {
            "agent_id": agent_id,
            "hostname": data.get("hostname"),
            "ip_address": data.get("ip_address"),
            "username": data.get("username"),
            "os": data.get("os"),
            "cpu": data.get("cpu"),
            "ram": data.get("ram"),
            "status": "online"
        }
        print(f" [+] Agent Connected: {agent_id} ")
    else:
        print("Agent connected without an ID")

@socketio.on("disconnect", namespace='/agent')
def handle_agent_disconnect():
    agent_info = connected_agents.pop(request.sid, None)
    for agent_id in remove_sid(request.sid):
        print(f"[STREAM CLOSED] {agent_id}")
    if agent_info:
        set_offline(agent_info["agent_id"])
        print(f" [-] Agent Disconnected: {agent_info['agent_id']} ")
    else:
        print("An agent disconnected without a known ID")

@socketio.on("heartbeat", namespace='/agent')
def handle_heartbeat(data):
    data = data or {}
    agent_id = data.get("agent_id")
    if not agent_id:
        return
    update_heartbeat(agent_id)
    for sid, info in connected_agents.items():
        if info["agent_id"] == agent_id:
            connected_agents[sid]["status"] = "online"
            print(f" [❤️] Heartbeat received from {agent_id} ")
            break
