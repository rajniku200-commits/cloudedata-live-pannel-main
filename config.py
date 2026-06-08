import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-on-prod')
SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(INSTANCE_DIR, 'database.db')
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
MONGODB_URI = os.getenv('MONGODB_URI', '')
SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
PREFERRED_URL_SCHEME = 'https'
