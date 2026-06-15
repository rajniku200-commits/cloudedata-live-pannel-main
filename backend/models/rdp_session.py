from datetime import datetime
from backend.extensions import db


class RdpSession(db.Model):
    __tablename__ = 'rdp_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    published_app_id = db.Column(db.Integer, db.ForeignKey('published_apps.id'), nullable=True)
    guac_token = db.Column(db.String(512), nullable=True)
    guac_connection_id = db.Column(db.String(255), nullable=True)
    connection_type = db.Column(db.String(10), default='rdp')
    status = db.Column(db.String(20), default='active')
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    started_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    last_seen_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    ended_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('rdp_sessions', lazy='dynamic'))
    server = db.relationship('Server', backref=db.backref('rdp_sessions', lazy='dynamic'))
    published_app = db.relationship('PublishedApp', backref=db.backref('rdp_sessions', lazy='dynamic'))

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def to_dict(self):
        duration = None
        if self.started_at:
            end = self.ended_at or datetime.utcnow()
            duration = int((end - self.started_at).total_seconds())
        return {
            'id': self.id,
            'user_id': self.user_id,
            'server_id': self.server_id,
            'published_app_id': self.published_app_id,
            'published_app_name': self.published_app.name if self.published_app else None,
            'guac_token': self.guac_token,
            'guac_connection_id': self.guac_connection_id,
            'connection_type': self.connection_type,
            'status': self.status,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_seconds': duration,
        }

    def close(self):
        self.status = 'closed'
        self.ended_at = datetime.utcnow()
        self.save()

    def ping(self):
        self.last_seen_at = datetime.utcnow()
        self.save()

    @classmethod
    def get_active(cls):
        return cls.query.filter_by(status='active').order_by(cls.started_at.desc()).all()

    @classmethod
    def get_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id).order_by(cls.started_at.desc()).all()

    @classmethod
    def get_active_by_user(cls, user_id):
        return cls.query.filter_by(user_id=user_id, status='active').first()
