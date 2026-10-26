import os
import secrets
import click
from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy import event
from sqlalchemy.engine import Engine

from hms_app.config import Config
from hms_app.models import db
from hms_app.auth import get_current_user, LoginThrottle

csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite (off by default)."""
    if dbapi_connection.__class__.__module__.startswith('sqlite3'):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config_class=Config):
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    app.config.from_object(config_class)

    db.init_app(app)
    csrf.init_app(app)
    app.extensions['login_throttle'] = LoginThrottle(
        max_attempts=app.config['LOGIN_MAX_ATTEMPTS'],
        lockout_seconds=app.config['LOGIN_LOCKOUT_SECONDS'])

    from hms_app.routes.auth_routes import auth_bp
    from hms_app.routes.room_allocation_routes import room_alloc_bp
    from hms_app.routes.main_routes import main_bp
    from hms_app.routes.admin_data_routes import admin_data_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(room_alloc_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_data_bp)

    @app.before_request
    def _csp_nonce():
        request.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inject_globals():
        return dict(current_user=get_current_user(),
                    csp_nonce=getattr(request, 'csp_nonce', ''),
                    app_name=app.config.get('APP_NAME', 'Hostel Management System'),
                    app_short_name=app.config.get('APP_SHORT_NAME', 'HMS'))

    @app.after_request
    def _security_headers(resp):
        nonce = getattr(request, 'csp_nonce', '')
        resp.headers.setdefault('Content-Security-Policy', (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"))
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'DENY')
        resp.headers.setdefault('Referrer-Policy', 'same-origin')
        resp.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if app.config.get('SESSION_COOKIE_SECURE'):
            resp.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        if request.endpoint != 'static':
            # Authenticated pages must not be served from the browser cache after logout.
            resp.headers.setdefault('Cache-Control', 'no-store')
        return resp

    @app.errorhandler(CSRFError)
    def _csrf_error(err):
        return render_template('csrf_error.html', reason=err.description), 400

    with app.app_context():
        db.create_all()
        if app.config.get('SEED_DEMO_DATA'):
            from hms_app.seed import seed_demo_data
            seed_demo_data()

    _register_cli(app)
    return app


def _register_cli(app):
    from hms_app import seed

    @app.cli.command('seed-demo')
    @click.option('--with-allocations', is_flag=True, help='Also allocate the demo students to rooms.')
    def seed_demo(with_allocations):
        """Load demo users/rooms (well-known passwords: demo use only)."""
        click.echo('Demo data created.' if seed.seed_demo_data() else 'Database is not empty; demo data skipped.')
        if with_allocations:
            click.echo(f'{seed.seed_demo_allocations()} demo allocation(s) created.')

    @app.cli.command('create-admin')
    @click.option('--name', prompt=True)
    @click.option('--email', prompt=True)
    @click.password_option()
    def create_admin(name, email, password):
        """Create an administrator account."""
        try:
            seed.create_admin_user(name, email, password)
        except ValueError as exc:
            raise click.ClickException(str(exc))
        click.echo(f'Administrator {email} created.')
