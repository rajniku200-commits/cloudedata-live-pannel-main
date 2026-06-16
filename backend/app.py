import os
from flask import Flask, redirect, url_for
from flask_login import current_user
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException
from backend.extensions import login_manager, socketio, db
from backend.models.user import User
from backend.models.server import Server
from backend.models.session import Session
from backend.models.rdp_session import RdpSession
from backend.models.activity_log import ActivityLog
from backend.models.agent import Agent
from backend.models.login_link import LoginLink
from backend.models.published_app import ApplicationAssignment, PublishedApp
from backend.models.ticket import ClipboardItem, Ticket
from backend.services.logger import configure_logging


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INSTANCE_DIR = os.path.join(ROOT_DIR, 'instance')
TEMPLATE_DIR = os.path.join(ROOT_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(ROOT_DIR, 'frontend', 'static')

app = Flask(
    __name__,
    instance_path=INSTANCE_DIR,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/static',
)
app.config.from_object('backend.config')
app.config.from_pyfile('config.py', silent=True)

app.config.setdefault('SQLALCHEMY_DATABASE_URI', os.getenv('DATABASE_URI', 'sqlite:///' + os.path.join(app.instance_path, 'app.db')))
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

os.makedirs(app.instance_path, exist_ok=True)
configure_logging(app)

login_manager.init_app(app)
login_manager.login_view = 'auth.login'
socketio.init_app(app)
db.init_app(app)

with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    if 'users' in inspector.get_table_names():
        user_columns = {column['name'] for column in inspector.get_columns('users')}
        if 'role' not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'User'"))
            db.session.commit()
        if 'is_active' not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
            db.session.commit()
        if 'last_login_at' not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))
            db.session.commit()
        if 'two_factor_enabled' not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN NOT NULL DEFAULT 0"))
            db.session.commit()
        if 'two_factor_secret' not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN two_factor_secret VARCHAR(64)"))
            db.session.commit()
        if User.query.count() and not User.query.filter_by(role='Admin').first():
            first_user = User.query.order_by(User.id.asc()).first()
            first_user.role = 'Admin'
            db.session.commit()
    if 'rdp_sessions' in inspector.get_table_names():
        session_columns = {column['name'] for column in inspector.get_columns('rdp_sessions')}
        if 'published_app_id' not in session_columns:
            db.session.execute(text("ALTER TABLE rdp_sessions ADD COLUMN published_app_id INTEGER"))
            db.session.commit()

import backend.sockets.socket_handler
import backend.sockets.stream_socket
from backend.routes.auth import auth
from backend.routes.files import files
from backend.routes.terminal import terminal
from backend.routes.server import server
from backend.routes.windows import windows
from backend.routes.process import process
from backend.routes.services_manager import services
from backend.routes.logs import logs
from backend.routes.portal import portal_bp
from backend.routes.sessions import sessions_bp
from backend.routes.apps import apps_bp
from backend.routes.admin_features import admin_features
from backend.routes.rdp import init_rdp_namespace
from backend.sockets.socket_handler import register_sockets
from backend.routes.agent import agent_bp


register_sockets()
init_rdp_namespace(socketio)

app.register_blueprint(auth)
app.register_blueprint(files)
app.register_blueprint(terminal)
app.register_blueprint(server)
app.register_blueprint(process)
app.register_blueprint(windows)
app.register_blueprint(services)
app.register_blueprint(logs)
app.register_blueprint(portal_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(apps_bp)
app.register_blueprint(agent_bp)
app.register_blueprint(admin_features)

def create_app():
    return app

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('portal.portal_home'))
    return redirect(url_for('auth.login'))

@app.route('/test')
def test():
    return 'test working'

@app.route('/test_socket')
def test_socket():
    socketio.emit('message', {'data': 'Hello from the server!'})
    return 'Socket test emitted'


@app.errorhandler(Exception)
def log_unhandled_exception(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.exception('Unhandled exception')
    raise error

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

if __name__ == '__main__':
    socketio.run(app,
    host='0.0.0.0',
    port=5000,
    debug=True,
    allow_unsafe_werkzeug=True)
