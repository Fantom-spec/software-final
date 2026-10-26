import re
import subprocess
import sys
import os
import pytest
from bs4 import BeautifulSoup
from hms_app.auth import LoginThrottle
from hms_app.models import db, User, Student, Room, RoomAllocation
from tests.helpers import make_app, populate, login, soup

pytestmark = pytest.mark.security
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def env():
    app = make_app(WTF_CSRF_ENABLED=True)
    return app, populate(app)


# ---------------------------------------------------------------- headers / CSP
PAGES = ['/', '/allocation/', '/allocation/create', '/allocation/available', '/rooms', '/students']


def _admin(app):
    c = app.test_client()
    login(c, 'admin@t.test', 'Admin#12345')
    return c


def test_security_headers_on_login_page(env):
    app, _ = env
    r = app.test_client().get('/auth/login')
    h = r.headers
    assert h['X-Content-Type-Options'] == 'nosniff'
    assert h['X-Frame-Options'] == 'DENY'
    assert h['Referrer-Policy'] == 'same-origin'
    assert h['Cache-Control'] == 'no-store'
    csp = h['Content-Security-Policy']
    assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert 'unsafe-inline' not in re.search(r"script-src[^;]*", csp).group(0)
    assert 'unsafe-eval' not in csp


def test_csp_nonce_is_per_request(env):
    app, _ = env
    c = app.test_client()
    n1 = re.search(r"'nonce-([^']+)'", c.get('/auth/login').headers['Content-Security-Policy']).group(1)
    n2 = re.search(r"'nonce-([^']+)'", c.get('/auth/login').headers['Content-Security-Policy']).group(1)
    assert n1 != n2 and len(n1) >= 16


@pytest.mark.parametrize('path', ['/auth/login'] + PAGES)
def test_pages_are_csp_clean_and_self_hosted(env, path):
    """Every inline script carries the request nonce; no inline handlers; no third-party hosts."""
    app, _ = env
    c = app.test_client() if path == '/auth/login' else _admin(app)
    r = c.get(path)
    assert r.status_code == 200
    nonce = re.search(r"'nonce-([^']+)'", r.headers['Content-Security-Policy']).group(1)
    s = soup(r)
    for sc in s.find_all('script'):
        assert sc.get('src') or sc.get('nonce') == nonce, f'inline script without nonce on {path}'
    for el in s.find_all(True):
        assert not [a for a in el.attrs if a.lower().startswith('on')], f'inline handler {el.name} on {path}'
    for el in s.find_all(['script', 'link', 'img']):
        url = el.get('src') or el.get('href') or ''
        assert not re.match(r'(https?:)?//', url), f'external resource {url} on {path}'


def test_vendored_assets_are_served(env):
    app, _ = env
    c = app.test_client()
    for u in ['/static/vendor/bootstrap/css/bootstrap.min.css', '/static/vendor/bootstrap/js/bootstrap.bundle.min.js',
              '/static/vendor/bootstrap-icons/bootstrap-icons.min.css', '/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2',
              '/static/css/hms.css']:
        assert c.get(u).status_code == 200, u


def test_session_cookie_flags(env):
    app, _ = env
    c = app.test_client()
    cookie = login(c, 'admin@t.test', 'Admin#12345').headers.get('Set-Cookie')
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie
    assert 'Secure' not in cookie  # opt-in: requires HTTPS


def test_secure_cookie_and_hsts_when_enabled():
    app = make_app(WTF_CSRF_ENABLED=True, SESSION_COOKIE_SECURE=True)
    populate(app)
    c = app.test_client()
    r = login(c, 'admin@t.test', 'Admin#12345')
    assert 'Secure' in r.headers['Set-Cookie']
    assert 'max-age=' in c.get('/auth/login').headers['Strict-Transport-Security']


# ---------------------------------------------------------------- defaults / secrets / seeding
def _run_config_probe(extra_env=None):
    env = {k: v for k, v in os.environ.items() if k not in ('SECRET_KEY', 'HMS_SEED_DEMO_DATA', 'SHOW_DEMO_CREDENTIALS', 'FLASK_DEBUG')}
    env.update(extra_env or {})
    code = "from hms_app.config import Config as C; print(C.SECRET_KEY, C.SEED_DEMO_DATA, C.SHOW_DEMO_CREDENTIALS)"
    out = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True, check=True).stdout.split()
    return out[0], out[1], out[2]


def test_no_hardcoded_secret_and_unsafe_defaults_off():
    k1, seed1, demo1 = _run_config_probe()
    k2, _, _ = _run_config_probe()
    assert (seed1, demo1) == ('False', 'False')
    assert len(k1) >= 32 and k1 != k2  # random per process, not a constant


def test_secret_key_from_environment_is_used():
    assert _run_config_probe({'SECRET_KEY': 'abc123xyz'})[0] == 'abc123xyz'


def test_run_entry_points_have_no_hardcoded_debug():
    for f in ('run.py', os.path.join('hms_app', '__main__.py')):
        src = open(os.path.join(ROOT, f)).read()
        assert 'debug=True' not in src
        assert "FLASK_DEBUG" in src


def test_app_is_not_in_debug_mode_by_default():
    assert make_app().debug is False


def test_no_users_seeded_by_default():
    app = make_app()
    with app.app_context():
        assert User.query.count() == 0


def test_login_page_hides_demo_credentials_by_default(env):
    app, _ = env
    r = app.test_client().get('/auth/login')
    html = r.get_data(as_text=True)
    assert soup(r).select('.demo-list') == [] and soup(r).select('[data-p]') == []
    for needle in ('admin123', 'warden123', 'student123', 'accountant123', 'admin@hms.test'):
        assert needle not in html


def test_demo_credentials_shown_only_when_explicitly_enabled():
    app = make_app(SHOW_DEMO_CREDENTIALS=True, SEED_DEMO_DATA=True)
    r = app.test_client().get('/auth/login')
    assert len(soup(r).select('.demo-list button[data-p]')) == 4


def _invoke(app, *args):
    """Run a CLI command with `app`'s context pushed explicitly.

    Flask's with_appcontext reuses an already-active context, and the suite-wide
    fixture keeps another app's context open, so without this the command would
    run against the wrong application."""
    with app.app_context():
        return app.test_cli_runner().invoke(args=list(args))


def test_seed_demo_cli_is_consistent():
    app = make_app()
    res = _invoke(app, 'seed-demo', '--with-allocations')
    assert res.exit_code == 0, res.output
    with app.app_context():
        assert RoomAllocation.query.filter_by(status='active').count() == 3
        for room in Room.query.all():
            assert room.occupied_beds == RoomAllocation.query.filter_by(room_id=room.room_id, status='active').count()
            assert room.status == ('full' if room.occupied_beds >= room.capacity else 'available')
    res2 = _invoke(app, 'seed-demo')
    assert 'skipped' in res2.output


def test_create_admin_cli_creates_working_login():
    app = make_app(WTF_CSRF_ENABLED=True)
    res = _invoke(app, 'create-admin', '--name', 'Ada', '--email', 'ada@x.test', '--password', 'Str0ng#Pass1')
    assert res.exit_code == 0, res.output
    assert login(app.test_client(), 'ada@x.test', 'Str0ng#Pass1').status_code == 302
    dup = _invoke(app, 'create-admin', '--name', 'Ada', '--email', 'ada@x.test', '--password', 'x')
    assert dup.exit_code != 0


# ---------------------------------------------------------------- login throttling
class TestLoginThrottle:
    def test_lockout_after_repeated_failures_blocks_even_correct_password(self, env):
        app, _ = env
        c = app.test_client()
        for _ in range(5):
            assert login(c, 'admin@t.test', 'wrong').status_code == 200
        r = login(c, 'admin@t.test', 'Admin#12345')
        assert r.status_code == 429
        assert 'too many' in r.get_data(as_text=True).lower()
        assert c.get('/').status_code == 302  # not logged in

    def test_other_accounts_unaffected(self, env):
        app, _ = env
        c = app.test_client()
        for _ in range(5):
            login(c, 'admin@t.test', 'wrong')
        assert login(c, 's1@t.test', 'Stud#12345').status_code == 302

    def test_success_resets_counter(self, env):
        app, _ = env
        c = app.test_client()
        for _ in range(4):
            login(c, 'admin@t.test', 'wrong')
        assert login(c, 'admin@t.test', 'Admin#12345').status_code == 302
        c.post('/auth/logout', data={'csrf_token': soup(c.get('/')).find('input', {'name': 'csrf_token'})['value']})
        for _ in range(4):
            assert login(c, 'admin@t.test', 'wrong').status_code == 200  # counter restarted

    def test_unit_lockout_expiry_and_per_address_isolation(self):
        now = [1000.0]
        app = make_app()
        th = LoginThrottle(max_attempts=3, lockout_seconds=60, clock=lambda: now[0])
        with app.test_request_context(environ_base={'REMOTE_ADDR': '10.0.0.1'}):
            for _ in range(3):
                th.record_failure('A@x.test')
            assert th.retry_after('a@x.test') > 0  # case-insensitive key
        with app.test_request_context(environ_base={'REMOTE_ADDR': '10.0.0.2'}):
            assert th.retry_after('a@x.test') == 0  # other address not locked out
        now[0] += 61
        with app.test_request_context(environ_base={'REMOTE_ADDR': '10.0.0.1'}):
            assert th.retry_after('a@x.test') == 0  # expired


# ---------------------------------------------------------------- sessions / redirects
class TestSessions:
    def test_session_for_nonexistent_user_is_treated_as_logged_out(self, env):
        app, _ = env
        c = app.test_client()
        with c.session_transaction() as s:
            s['user_id'] = 99999
            s['user_role'] = 'admin'
        r = c.get('/')
        assert r.status_code == 302 and '/auth/login' in r.headers['Location']
        with c.session_transaction() as s:
            assert 'user_id' not in s

    def test_deleted_user_does_not_cause_500(self, env):
        app, ids = env
        c = app.test_client()
        login(c, 's2@t.test', 'Stud#12345')
        with app.app_context():
            u = User.query.filter_by(email='s2@t.test').first()
            Student.query.filter_by(user_id=u.user_id).delete()
            db.session.delete(u)
            db.session.commit()
        for path in ('/', '/allocation/available', f"/allocation/student/{ids['student_ids'][1]}"):
            r = c.get(path)
            assert r.status_code in (302, 200), path
            assert r.status_code != 500

    @pytest.mark.parametrize('nxt,expected_prefix', [('//evil.example', '/'), ('/\\evil.example', '/'), ('https://evil.example', '/'), ('/rooms', '/rooms')])
    def test_next_param_cannot_redirect_off_site(self, env, nxt, expected_prefix):
        app, _ = env
        c = app.test_client()
        from tests.helpers import token
        r = c.post(f'/auth/login?next={nxt}', data={'email': 'admin@t.test', 'password': 'Admin#12345', 'csrf_token': token(c, '/auth/login')})
        loc = r.headers['Location']
        assert 'evil.example' not in loc
        assert loc.startswith(expected_prefix)
