from extensions import db

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    host = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    
    def to_dict(self):
        """Serialize server to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.host,
            'rdp_port': self.port,
            'connection_type': 'rdp',
            'os_type': 'Windows',
            'description': '',
            'is_active': True
        }
