from flask_login import UserMixin
from backend.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    ROLES = ('Super Admin', 'Admin', 'Manager', 'Viewer', 'User')

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='User')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    two_factor_enabled = db.Column(db.Boolean, nullable=False, default=False)
    two_factor_secret = db.Column(db.String(64), nullable=True)

    @classmethod
    def normalize_role(cls, role):
        aliases = {'superadmin': 'Super Admin', 'super_admin': 'Super Admin'}
        raw = (role or 'User').strip()
        value = aliases.get(raw.lower().replace(' ', ''), raw.title())
        if value not in cls.ROLES:
            raise ValueError(f'Invalid role. Allowed roles: {", ".join(cls.ROLES)}')
        return value

    def set_role(self, role):
        self.role = self.normalize_role(role)
        return self

    def has_role(self, *roles):
        if self.role == 'Super Admin':
            return True
        return self.role in roles

    @property
    def is_admin(self):
        return self.role in ('Super Admin', 'Admin')

    @property
    def is_manager(self):
        return self.role in ('Super Admin', 'Admin', 'Manager')

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'is_active': bool(self.is_active),
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'two_factor_enabled': bool(self.two_factor_enabled),
        }

    @classmethod
    def get_by_id(cls, id):
        if id is None:
            return None
        try:
            return db.session.get(cls, int(id))
        except (TypeError, ValueError):
            return None

    @classmethod
    def find_by_username(cls, username):
        if not username:
            return None
        return cls.query.filter_by(username=username).first()

    @classmethod
    def username_exists(cls, username):
        return cls.query.filter_by(username=username).count() > 0
