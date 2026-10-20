import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hms-test-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hms.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Show demo logins on the login page (turn off in production)
    SHOW_DEMO_CREDENTIALS = os.environ.get('SHOW_DEMO_CREDENTIALS', '1') == '1'
    # Application name for branding
    APP_NAME = 'Hostel Management System'
    APP_SHORT_NAME = 'HMS'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_hms.db'
    WTF_CSRF_ENABLED = True
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_TIME_LIMIT = None
    SHOW_DEMO_CREDENTIALS = False