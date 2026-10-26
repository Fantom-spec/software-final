import logging
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

_log = logging.getLogger(__name__)


def _secret_key():
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    # No hard-coded fallback: an unset key yields a random per-process key.
    # Sessions then do not survive a restart, which is the safe failure mode.
    _log.warning('SECRET_KEY is not set; using a random per-process key. '
                 'Set SECRET_KEY in the environment for stable sessions.')
    return secrets.token_hex(32)


def _flag(name, default='0'):
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


class Config:
    SECRET_KEY = _secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hms.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # CSRF token is tied to the session lifetime

    # Session cookie hardening. SECURE needs HTTPS, so it is opt-in via the
    # environment (set SESSION_COOKIE_SECURE=1 in any HTTPS deployment).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _flag('SESSION_COOKIE_SECURE')
    PERMANENT_SESSION_LIFETIME = 8 * 60 * 60  # seconds

    # Demo data / credentials are strictly opt-in.
    SEED_DEMO_DATA = _flag('HMS_SEED_DEMO_DATA')
    SHOW_DEMO_CREDENTIALS = _flag('SHOW_DEMO_CREDENTIALS')

    # Login throttling
    LOGIN_MAX_ATTEMPTS = int(os.environ.get('LOGIN_MAX_ATTEMPTS', '5'))
    LOGIN_LOCKOUT_SECONDS = int(os.environ.get('LOGIN_LOCKOUT_SECONDS', '900'))

    # Sanity range for allocation dates
    MIN_ALLOCATION_DATE = '2000-01-01'
    MAX_ALLOCATION_DATE = '2100-12-31'

    APP_NAME = 'Hostel Management System'
    APP_SHORT_NAME = 'HMS'


class TestConfig(Config):
    """General-purpose test config. CSRF is off here only so that the many
    behavior tests need not fetch a token; CSRF itself is tested separately in
    tests/test_csrf.py against an app with protection ON."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-only-secret-key'
    SEED_DEMO_DATA = False
    SHOW_DEMO_CREDENTIALS = False
    LOGIN_MAX_ATTEMPTS = 5
