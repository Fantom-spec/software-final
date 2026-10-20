from urllib.parse import urlparse
from flask import session, redirect, url_for, flash, request
from functools import wraps
from hms_app.models import db, User


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))
            user = User.query.get(session['user_id'])
            if not user or user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


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