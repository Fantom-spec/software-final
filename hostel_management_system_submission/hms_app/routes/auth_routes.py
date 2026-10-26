from flask import current_app, Blueprint, render_template, redirect, url_for, flash, request
from hms_app.models import db, User
from hms_app.auth import (login_user, logout_user, login_required, is_safe_next,
                          get_current_user, get_throttle)


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def _render_login(status=200):
    return render_template('login.html', demo=current_app.config.get('SHOW_DEMO_CREDENTIALS')), status


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and get_current_user():
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'error')
            return _render_login()

        throttle = get_throttle()
        wait = throttle.retry_after(email)
        if wait:
            minutes = (wait + 59) // 60
            flash(f'Too many failed login attempts. Try again in about {minutes} minute(s).', 'error')
            return _render_login(429)

        user = User.query.filter(db.func.lower(User.email) == email).first()

        if user and user.check_password(password):
            throttle.reset(email)
            login_user(user)
            flash(f'Welcome, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if is_safe_next(next_page) else url_for('main.dashboard'))
        throttle.record_failure(email)
        flash('Invalid email or password.', 'error')

    return _render_login()


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """POST-only; CSRFProtect rejects it without a valid token, so a third-party
    page cannot log a user out by embedding a link or image."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
