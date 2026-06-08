"""
models/rdp_session.py
Stores active and historical RDP sessions.
Matches structure of: models/user.py, models/server.py, models/session.py
"""

from datetime import datetime
from extensions import db


class RdpSession(db.Model):
    __tablename__ = "rdp_sessions"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    server_id        = db.Column(db.Integer, db.ForeignKey("servers.id"), nullable=False)

    # Guacamole connection info
    guac_token       = db.Column(db.String(512), nullable=True)   # auth token from Guacamole
    guac_connection_id = db.Column(db.String(255), nullable=True) # Guacamole connection identifier
    connection_type  = db.Column(db.String(10), default="rdp")    # rdp | ssh | vnc

    # Session state
    status           = db.Column(db.String(20), default="active")  # active | closed | error
    ip_address       = db.Column(db.String(45), nullable=True)     # client IP
    user_agent       = db.Column(db.String(255), nullable=True)

    # Timestamps
    started_at       = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen_at     = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at         = db.Column(db.DateTime, nullable=True)

    # Relationships
    user   = db.relationship("User",   backref=db.backref("rdp_sessions", lazy="dynamic"))
    server = db.relationship("Server", backref=db.backref("rdp_sessions", lazy="dynamic"))

    def __repr__(self):
        return f"<RdpSession {self.id} user={self.user_id} server={self.server_id} status={self.status}>"

    def to_dict(self):
        duration = None
        if self.started_at:
            end = self.ended_at or datetime.utcnow()
            duration = int((end - self.started_at).total_seconds())
        return {
            "id":                 self.id,
            "user_id":            self.user_id,
            "server_id":          self.server_id,
            "guac_token":         self.guac_token,
            "guac_connection_id": self.guac_connection_id,
            "connection_type":    self.connection_type,
            "status":             self.status,
            "ip_address":         self.ip_address,
            "started_at":         self.started_at.isoformat() if self.started_at else None,
            "last_seen_at":       self.last_seen_at.isoformat() if self.last_seen_at else None,
            "ended_at":           self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds":   duration,
        }

    def close(self):
        self.status   = "closed"
        self.ended_at = datetime.utcnow()
        db.session.commit()

    def ping(self):
        self.last_seen_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def get_active(cls):
        return cls.query.filter_by(status="active").order_by(cls.started_at.desc()).all()

    @classmethod
    def get_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).order_by(cls.started_at.desc()).all()

    @classmethod
    def get_active_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id, status="active").first()