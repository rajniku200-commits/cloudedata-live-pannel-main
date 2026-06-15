from datetime import datetime

from backend.extensions import db


class PublishedApp(db.Model):
    __tablename__ = 'published_apps'

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(128), unique=True, nullable=False)
    icon = db.Column(db.String(64), nullable=False, default='app')
    launch_mode = db.Column(db.String(32), nullable=False, default='remote_app')
    remote_app_program = db.Column(db.String(512), nullable=True)
    initial_program = db.Column(db.String(512), nullable=True)
    working_directory = db.Column(db.String(512), nullable=True)
    arguments = db.Column(db.String(1024), nullable=True)
    description = db.Column(db.String(512), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    server = db.relationship('Server', backref=db.backref('published_apps', lazy='dynamic'))
    assignments = db.relationship(
        'ApplicationAssignment',
        back_populates='app',
        cascade='all, delete-orphan',
        lazy='dynamic',
    )

    @classmethod
    def get_by_id(cls, app_id):
        if app_id is None:
            return None
        try:
            return db.session.get(cls, int(app_id))
        except (TypeError, ValueError):
            return None

    @classmethod
    def assigned_to_user(cls, user_id):
        return (
            cls.query
            .join(ApplicationAssignment)
            .filter(
                cls.is_active.is_(True),
                ApplicationAssignment.user_id == user_id,
                ApplicationAssignment.is_enabled.is_(True),
            )
            .order_by(cls.name.asc())
            .all()
        )

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def to_dict(self, include_server=True):
        data = {
            'id': self.id,
            'server_id': self.server_id,
            'name': self.name,
            'slug': self.slug,
            'icon': self.icon,
            'launch_mode': self.launch_mode,
            'remote_app_program': self.remote_app_program,
            'initial_program': self.initial_program,
            'working_directory': self.working_directory,
            'arguments': self.arguments,
            'description': self.description or '',
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_server and self.server:
            data['server'] = self.server.to_dict()
        return data


class ApplicationAssignment(db.Model):
    __tablename__ = 'application_assignments'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'app_id', name='uq_application_assignments_user_app'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    app_id = db.Column(db.Integer, db.ForeignKey('published_apps.id'), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    assigned_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('application_assignments', lazy='dynamic'))
    app = db.relationship('PublishedApp', back_populates='assignments')

    @classmethod
    def find(cls, user_id, app_id):
        return cls.query.filter_by(user_id=user_id, app_id=app_id).first()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'app_id': self.app_id,
            'is_enabled': self.is_enabled,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'app': self.app.to_dict() if self.app else None,
        }
