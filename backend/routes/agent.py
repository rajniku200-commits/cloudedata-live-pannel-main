from flask import Blueprint, jsonify
from backend.models.agent import Agent

agent_bp = Blueprint('agent', __name__)


def serialize_agent(agent):
    return {
        "agent_id": agent.agent_id,
        "hostname": agent.hostname,
        "ip_address": agent.ip_address,
        "username": agent.username,
        "os": agent.os,
        "cpu": agent.cpu,
        "ram": agent.ram,
        "status": agent.status,
        "last_seen": agent.last_seen.isoformat() if agent.last_seen else None
    }


@agent_bp.route('/agents', methods=['GET'])
def get_agents():
    agents = Agent.query.all()
    return jsonify([serialize_agent(agent) for agent in agents])


@agent_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(serialize_agent(agent))
