from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
socketio = SocketIO(
    cors_allowed_origins="*",
)
db = SQLAlchemy()
