from flask import current_app, Blueprint, render_template, redirect, url_for, flash, request, session
from hms_app.models import db, User
from hms_app.auth import login_user, logout_user, login_required, role_required, is_safe_next, get_current_user


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and get_current_user():
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('login.html', demo=current_app.config.get('SHOW_DEMO_CREDENTIALS'))
        
        user = User.query.filter(db.func.lower(User.email) == email).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if is_safe_next(next_page) else url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html', demo=current_app.config.get('SHOW_DEMO_CREDENTIALS'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))