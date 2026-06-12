from backend.models.agent import Agent
from backend.models.server import Server
from backend.extensions import db
from datetime import datetime


def register_agent(agent_id, hostname, ip_address, username, os, cpu, ram):
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if agent:
        agent.hostname = hostname
        agent.ip_address = ip_address
        agent.username = username
        agent.os = os
        agent.cpu = cpu
        agent.ram = ram
        agent.status = 'online'
        agent.last_seen = datetime.utcnow()
    else:
        new_agent = Agent(
            agent_id=agent_id,
            hostname=hostname,
            ip_address=ip_address,
            username=username,
            os=os,
            cpu=cpu,
            ram=ram,
            status='online',
            last_seen=datetime.utcnow()
        )
        db.session.add(new_agent)
    db.session.commit()

def update_heartbeat(agent_id):
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if agent:
        agent.status = 'online'
        agent.last_seen = datetime.utcnow()
        db.session.commit()

def set_offline(agent_id):
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if agent:
        agent.status = 'offline'
        agent.last_seen = datetime.utcnow()
        db.session.commit()