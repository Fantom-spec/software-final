"""CSRF protection, tested for real: the app under test has CSRF ENABLED.

(The general fixtures disable CSRF for convenience; that is why these tests use
their own app instance, created without a long-lived app context so Flask-WTF
cannot cache a token across requests.)
"""
import pytest
from datetime import date
from hms_app.models import db, RoomAllocation, Room
from tests.helpers import make_app, populate, token, login, count_allocations

pytestmark = pytest.mark.security


@pytest.fixture
def env():
    app = make_app(WTF_CSRF_ENABLED=True)
    ids = populate(app)
    return app, ids


def admin_client(app):
    c = app.test_client()
    assert login(c, 'admin@t.test', 'Admin#12345').status_code == 302
    return c


def create_payload(ids, **extra):
    d = dict(student_id=ids['student_ids'][0], room_id=ids['room_ids'][0], start_date=date.today().isoformat())
    d.update(extra)
    return d


def test_csrf_is_really_enabled(env):
    app, _ = env
    assert app.config['WTF_CSRF_ENABLED'] is True


class TestLogin:
    def test_missing_token_rejected(self, env):
        app, _ = env
        r = app.test_client().post('/auth/login', data={'email': 'admin@t.test', 'password': 'Admin#12345'})
        assert r.status_code == 400

    def test_invalid_token_rejected(self, env):
        app, _ = env
        r = app.test_client().post('/auth/login', data={'email': 'admin@t.test', 'password': 'Admin#12345', 'csrf_token': 'forged'})
        assert r.status_code == 400

    def test_valid_token_accepted(self, env):
        app, _ = env
        assert login(app.test_client(), 'admin@t.test', 'Admin#12345').status_code == 302

    def test_rejected_login_does_not_create_session(self, env):
        app, _ = env
        c = app.test_client()
        c.post('/auth/login', data={'email': 'admin@t.test', 'password': 'Admin#12345'})
        assert c.get('/').status_code == 302  # still anonymous


class TestCreateAllocation:
    def test_missing_token_rejected_and_nothing_created(self, env):
        app, ids = env
        c = admin_client(app)
        assert c.post('/allocation/create', data=create_payload(ids)).status_code == 400
        assert count_allocations(app) == 0

    def test_invalid_token_rejected_and_nothing_created(self, env):
        app, ids = env
        c = admin_client(app)
        assert c.post('/allocation/create', data=create_payload(ids, csrf_token='forged')).status_code == 400
        assert count_allocations(app) == 0

    def test_valid_token_creates_allocation(self, env):
        app, ids = env
        c = admin_client(app)
        r = c.post('/allocation/create', data=create_payload(ids, csrf_token=token(c, '/allocation/create')))
        assert r.status_code == 302
        assert count_allocations(app, status='active') == 1

    def test_token_from_another_session_rejected(self, env):
        app, ids = env
        a = admin_client(app)
        other = app.test_client()
        login(other, 'admin@t.test', 'Admin#12345')
        stolen = token(a, '/allocation/create')
        assert other.post('/allocation/create', data=create_payload(ids, csrf_token=stolen)).status_code == 400
        assert count_allocations(app) == 0


class TestStateChangingActions:
    def _allocate(self, app, ids):
        c = admin_client(app)
        c.post('/allocation/create', data=create_payload(ids, csrf_token=token(c, '/allocation/create')))
        with app.app_context():
            return c, RoomAllocation.query.first().allocation_id

    def test_cancel_without_token_rejected_and_allocation_kept(self, env):
        app, ids = env
        c, aid = self._allocate(app, ids)
        assert c.post(f'/allocation/{aid}/cancel', data={}).status_code == 400
        assert count_allocations(app, status='active') == 1

    def test_cancel_with_token_works(self, env):
        app, ids = env
        c, aid = self._allocate(app, ids)
        t = token(c, '/allocation/')
        assert c.post(f'/allocation/{aid}/cancel', data={'csrf_token': t}).status_code == 302
        assert count_allocations(app, status='cancelled') == 1

    def test_reallocate_without_token_rejected_and_room_unchanged(self, env):
        app, ids = env
        c, aid = self._allocate(app, ids)
        r = c.post(f'/allocation/{aid}/reallocate', data={'new_room_id': ids['room_ids'][1]})
        assert r.status_code == 400
        with app.app_context():
            assert db.session.get(RoomAllocation, aid).room_id == ids['room_ids'][0]

    def test_logout_without_token_rejected_and_session_kept(self, env):
        app, _ = env
        c = admin_client(app)
        assert c.post('/auth/logout', data={}).status_code == 400
        assert c.get('/').status_code == 200  # still logged in

    def test_logout_with_token_ends_session(self, env):
        app, _ = env
        c = admin_client(app)
        assert c.post('/auth/logout', data={'csrf_token': token(c, '/')}).status_code == 302
        assert c.get('/').status_code == 302

    def test_logout_get_cannot_be_used_as_csrf_vector(self, env):
        app, _ = env
        c = admin_client(app)
        assert c.get('/auth/logout').status_code == 405
        assert c.get('/').status_code == 200
