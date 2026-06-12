from datetime import datetime
from backend.extensions import db


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(128), nullable=True)
    server_id = db.Column(db.Integer, nullable=True)
    session_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    @classmethod
    def log(cls, user_id=None, action=None, category=None, server_id=None, session_id=None, ip_address=None):
        entry = cls(
            user_id=user_id,
            action=action,
            category=category,
            server_id=server_id,
            session_id=session_id,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    @classmethod
    def recent(cls, limit=100):
        return cls.query.order_by(cls.timestamp.desc()).limit(limit).all()
