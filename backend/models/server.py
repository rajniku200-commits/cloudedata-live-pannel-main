from backend.extensions import db


class Server(db.Model):
    __tablename__ = 'servers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    host = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, id):
        if id is None:
            return None
        try:
            return db.session.get(cls, int(id))
        except (TypeError, ValueError):
            return None

    @classmethod
    def find_all(cls):
        return cls.query.all()

    @classmethod
    def find_active(cls):
        return cls.query.filter_by(is_active=True).all()

    @property
    def ip_address(self):
        return self.host

    @property
    def rdp_port(self):
        return self.port

    @property
    def rdp_username(self):
        return self.username

    @property
    def rdp_password(self):
        return self.password

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.host,
            'rdp_port': self.port,
            'connection_type': 'rdp',
            'os_type': 'Windows',
            'description': '',
            'is_active': self.is_active,
        }
