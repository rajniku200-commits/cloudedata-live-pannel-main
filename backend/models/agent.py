from backend.extensions import db
from datetime import datetime

class Agent(db.Model):
    __tablename__ = 'agents'
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.String(64), unique=True, nullable=False)
    hostname = db.Column(db.String(128))
    ip_address = db.Column(db.String(45))
    username = db.Column(db.String(64))
    os = db.Column(db.String(128))
    cpu = db.Column(db.String(128))
    ram = db.Column(db.String(128))
    status = db.Column(db.String(20), default='online')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Agent {self.agent_id} - {self.hostname} ({self.ip_address})>"