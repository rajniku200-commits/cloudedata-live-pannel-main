from datetime import datetime

from backend.extensions import db


class LoginLink(db.Model):
    __tablename__ = 'login_links'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    one_time = db.Column(db.Boolean, nullable=False, default=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('login_links', lazy='dynamic'))

    @property
    def is_valid(self):
        now = datetime.utcnow()
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at <= now:
            return False
        if self.one_time and self.used_at:
            return False
        return True

    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'one_time': bool(self.one_time),
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_valid': self.is_valid,
        }
