import threading
import time
from urllib.parse import urlparse
from flask import session, redirect, url_for, flash, request, current_app
from functools import wraps
from hms_app.models import db, User


def get_current_user():
    """Return the logged-in user, or None.

    A session that points at a user who no longer exists (deleted account) is
    treated as logged out and cleared, instead of causing errors downstream.
    """
    user_id = session.get('user_id')
    if user_id is None:
        return None
    user = db.session.get(User, user_id)
    if user is None:
        session.clear()
    return user


def _redirect_to_login():
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if get_current_user() is None:
            return _redirect_to_login()
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return _redirect_to_login()
            if user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def is_safe_next(target):
    """Only allow same-site relative redirect targets (prevents open redirects)."""
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target:
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc


def login_user(user):
    session.clear()  # prevent session fixation
    session['user_id'] = user.user_id
    session['user_role'] = user.role
    session['user_name'] = user.name


def logout_user():
    session.clear()


class LoginThrottle:
    """Per-process lockout after repeated failed logins.

    Keyed by (client address, e-mail) so an attacker cannot lock a real user out
    from other addresses. State is in memory: it resets on restart and is not
    shared between worker processes (use a shared store such as Redis if the
    app is ever run with several workers).
    """

    def __init__(self, max_attempts=5, lockout_seconds=900, clock=time.monotonic):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._state = {}  # key -> [failure_count, window_start, locked_until]

    def _key(self, email):
        return (request.remote_addr or '-', (email or '').strip().lower())

    def retry_after(self, email):
        """Seconds left on an active lockout, or 0."""
        with self._lock:
            entry = self._state.get(self._key(email))
            if not entry:
                return 0
            remaining = entry[2] - self._clock()
            return int(remaining) + 1 if remaining > 0 else 0

    def record_failure(self, email):
        now = self._clock()
        with self._lock:
            entry = self._state.setdefault(self._key(email), [0, now, 0.0])
            if now - entry[1] > self.lockout_seconds:  # stale window: start over
                entry[0], entry[1], entry[2] = 0, now, 0.0
            entry[0] += 1
            if entry[0] >= self.max_attempts:
                entry[2] = now + self.lockout_seconds

    def reset(self, email):
        with self._lock:
            self._state.pop(self._key(email), None)


def get_throttle():
    return current_app.extensions['login_throttle']
