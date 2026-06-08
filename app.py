import os
from flask import Flask
from models.user import User
from extensions import db, login_manager, socketio

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py', silent=True)

mongo_uri = app.config.get('MONGODB_URI')
if mongo_uri:
    try:
        import pymongo
        mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        mongo_client.server_info()
        app.mongo_client = mongo_client
    except Exception as exc:
        raise RuntimeError(f'MongoDB connection failed: {exc}')

app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
app.config.setdefault('REMEMBER_COOKIE_HTTPONLY', True)
app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
if app.config.get('ENV') == 'production':
    app.config.setdefault('SESSION_COOKIE_SECURE', True)

instance_path = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(instance_path, exist_ok=True)

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
socketio.init_app(app)
import sockets.socket_handler

from routes.auth import auth
from routes.files import files
from routes.terminal import terminal
from routes.server import server
from routes.windows import windows
from routes.process import process
from routes.services_manager import services
from routes.logs import logs
from routes.portal import portal_bp

app.register_blueprint(auth)
app.register_blueprint(files)
app.register_blueprint(terminal)
app.register_blueprint(server)
app.register_blueprint(process)
app.register_blueprint(windows)
app.register_blueprint(services)
app.register_blueprint(logs)
app.register_blueprint(portal_bp)
@app.route('/')
def home():
    return "Backend Running"

@app.route('/test')
def test():
    return "test working"
@app.route('/test_socket')
def test_socket():
    socketio.emit('message', {'data': 'Hello from the server!'})
    return "Socket test emitted"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    socketio.run(app, debug=True)