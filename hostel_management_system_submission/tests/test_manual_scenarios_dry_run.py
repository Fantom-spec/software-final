"""Scripted walk-through of the manual test sheet (assessment8_testing/manual_testing/manual_test_cases.csv).

PURPOSE: confirm that the expected results written in the manual sheet are what the
application actually does, and keep them true. This is an AUTOMATED dry run. It is NOT
evidence that a human executed the manual cases and must never be recorded as such.

Runs the sheet's main path in order against an app with CSRF enabled and demo data.
"""
from datetime import date, timedelta
import pytest
from hms_app.models import db, Room, Student, RoomAllocation
from tests.helpers import make_app, token, login, soup

TODAY = date.today().isoformat()


def text(resp):
    return soup(resp).get_text(' ', strip=True)


def flashes(resp):
    return [a.get_text(' ', strip=True) for a in soup(resp).select('.alert-dismissible')]


@pytest.fixture(scope='module')
def world():
    app = make_app(WTF_CSRF_ENABLED=True, SEED_DEMO_DATA=True)
    return app


class Session:
    def __init__(self, app, email, password):
        self.app, self.c = app, app.test_client()
        r = login(self.c, email, password)
        assert r.status_code == 302, (email, r.status_code)

    def create(self, student, room, start=TODAY, end='', csrf=True):
        data = dict(student_id=student, room_id=room, start_date=start, end_date=end)
        if csrf is True:
            data['csrf_token'] = token(self.c, '/allocation/create')
        elif csrf:
            data['csrf_token'] = csrf
        return self.c.post('/allocation/create', data=data, follow_redirects=True)

    def realloc(self, alloc_id, room):
        return self.c.post(f'/allocation/{alloc_id}/reallocate', data=dict(new_room_id=room, csrf_token=token(self.c, f'/allocation/{alloc_id}/reallocate')), follow_redirects=True)


def room_state(app, rid):
    with app.app_context():
        r = db.session.get(Room, rid)
        return r.occupied_beds, r.status


def alloc_id(app, student_id):
    with app.app_context():
        return RoomAllocation.query.filter_by(student_id=student_id, status='active').first().allocation_id


# demo ids: students John=1 Jane=2 Bob=3 Alice=4 Carlos=5 Dana=6 ; rooms A101=1 A102=2 A201=3 A202=4 B101=5 B102=6
JOHN, JANE, BOB, ALICE, CARLOS, DANA = 1, 2, 3, 4, 5, 6
A101, A102, A201, A202, B101, B102 = 1, 2, 3, 4, 5, 6


def test_sheet_main_path(world):
    app = world
    # ---- AUTH
    anon = app.test_client()
    r = login(anon, 'admin@hms.test', 'wrong-password', with_token=True)  # AUTH-04
    assert 'Invalid email or password.' in text(r)
    assert 'Invalid email or password.' in text(login(anon, 'nobody@example.com', 'x'))  # AUTH-05
    for path in ('/', '/allocation/', '/rooms'):  # AUTH-07
        r = anon.get(path, follow_redirects=True)
        assert 'Please log in to access this page.' in text(r)
    admin = Session(app, 'admin@hms.test', 'admin123')
    assert 'Welcome, Admin User!' in text(admin.c.get('/'))  # AUTH-01 (flash is consumed on first render after redirect)
    # AUTH-10 / AUTH-06
    assert admin.c.get('/auth/logout').status_code == 405
    assert admin.c.get('/').status_code == 200

    # ---- ALLOC
    assert 'Room 101 allocated to John Doe successfully.' in text(admin.create(JOHN, A101))  # ALLOC-01
    r = admin.create(JANE, A101, end=(date.today() + timedelta(days=90)).isoformat())  # ALLOC-08
    assert 'Room 101 allocated to Jane Smith successfully.' in text(r)
    assert room_state(app, A101) == (2, 'full')  # OCC-01
    r = admin.create(JOHN, B101)  # ALLOC-05
    assert 'Student John Doe already has an active room allocation.' in text(r)
    s = soup(r)  # ALLOC-15: form re-rendered with the user's choices kept
    assert s.select_one('#student_id option[selected]')['value'] == str(JOHN)
    assert s.select_one('#room_id option[selected]')['value'] == str(B101)
    assert 'Room 102 allocated to Bob Wilson successfully.' in text(admin.create(BOB, A102, end=TODAY))  # ALLOC-11
    assert 'Room 102 allocated to Alice Brown successfully.' in text(admin.create(ALICE, A102))
    r = admin.create(CARLOS, A102)  # ALLOC-02 (stale form: room 102 was still listed)
    assert 'Room 102 is not available (capacity: 2, occupied: 2).' in text(r)
    assert room_state(app, A102) == (2, 'full')
    warden = Session(app, 'warden@hms.test', 'warden123')
    assert 'Room 201 allocated to Carlos Diaz successfully.' in text(warden.create(CARLOS, A201))  # ALLOC-09
    assert 'Selected student does not exist.' in text(admin.create(99999, A202))  # ALLOC-03
    assert 'Selected room does not exist.' in text(admin.create(DANA, 99999))  # ALLOC-04
    assert 'Student, room, and start date are required.' in text(admin.create('', ''))  # ALLOC-06 (server fallback)
    assert 'Invalid date format. Use YYYY-MM-DD.' in text(admin.create(DANA, A202, start='2026-13-45'))  # ALLOC-07
    r = admin.create(DANA, A202, start=(date.today() + timedelta(days=10)).isoformat(), end=(date.today() + timedelta(days=5)).isoformat())  # ALLOC-10
    assert 'End date cannot be earlier than start date.' in text(r)
    for bad in ('1900-01-01', '9999-12-31'):  # ALLOC-14
        assert 'Dates must be between 2000-01-01 and 2100-12-31.' in text(admin.create(DANA, A202, start=bad))
    r = admin.create(DANA, A202, csrf=False)  # ALLOC-13
    assert r.status_code == 400 and 'could not be verified' in text(r)
    assert admin.create(DANA, A202, csrf='forged').status_code == 400  # SEC-05
    with app.app_context():
        assert RoomAllocation.query.filter_by(student_id=DANA).count() == 0

    # ---- REALLOC
    john_alloc = alloc_id(app, JOHN)
    assert 'Student reallocated to room 101 successfully.' in text(admin.realloc(john_alloc, B101))  # REALLOC-01
    assert room_state(app, A101) == (1, 'available') and room_state(app, B101) == (1, 'available')  # OCC-02
    carlos_alloc = alloc_id(app, CARLOS)
    options = [o['value'] for o in soup(admin.c.get(f'/allocation/{carlos_alloc}/reallocate')).select('#new_room_id option') if o['value']]
    assert str(A102) not in options  # REALLOC-03: full room not offered
    assert 'Student is already in that room. Choose a different room.' in text(admin.realloc(alloc_id(app, JANE), A101))  # REALLOC-06
    assert 'New room is required.' in text(admin.realloc(john_alloc, ''))  # REALLOC-04
    assert 'Selected room does not exist.' in text(admin.realloc(john_alloc, 99999))  # REALLOC-02
    r = admin.c.post(f'/allocation/{john_alloc}/reallocate', data=dict(new_room_id=B102))  # REALLOC-05
    assert r.status_code == 400

    # ---- CANCEL
    r = admin.c.post(f'/allocation/{carlos_alloc}/cancel', data={})  # CANCEL-03
    assert r.status_code == 400 and alloc_id(app, CARLOS) == carlos_alloc
    r = admin.c.post(f'/allocation/{carlos_alloc}/cancel', data=dict(csrf_token=token(admin.c, '/allocation/')), follow_redirects=True)
    assert 'Allocation cancelled successfully.' in text(r)  # CANCEL-01
    assert room_state(app, A201) == (0, 'available')
    rows = soup(admin.c.get('/allocation/?status=cancelled')).select('table tbody tr')  # CANCEL-04
    assert len(rows) == 1 and 'Carlos Diaz' in rows[0].get_text() and rows[0].select('form, a[href*="reallocate"]') == []

    # ---- LIST / AVAIL
    rows = soup(admin.c.get('/allocation/?search=Jane')).select('table tbody tr')  # LIST-01
    assert len(rows) == 1 and 'Jane Smith' in rows[0].get_text()
    assert 'No allocations found.' in text(admin.c.get('/allocation/?search=nobody-matches'))
    rows = soup(admin.c.get('/allocation/?block=2')).select('table tbody tr')  # LIST-02 (Block B = id 2)
    assert rows and all('Block B' in r.get_text() for r in rows)
    main = soup(admin.c.get('/allocation/available')).find('main')  # AVAIL-01
    for sel in main.find_all('select'):
        sel.decompose()
    assert 'Block A' in main.get_text() and room_state(app, A102) == (2, 'full')
    allm = soup(admin.c.get('/allocation/available?show_all=true&block=2')).find('main')  # AVAIL-03
    for sel in allm.find_all('select'):
        sel.decompose()
    assert 'Block A' not in allm.get_text() and 'Block B' in allm.get_text()
    rooms = [o['value'] for o in soup(admin.c.get('/allocation/create')).select('#room_id option') if o['value']]
    assert str(A102) not in rooms  # OCC-03

    # ---- SEC search payloads
    for payload in ("' OR '1'='1", "'; DROP TABLE rooms; --"):  # SEC-01
        assert admin.c.get('/allocation/', query_string={'search': payload}).status_code == 200
    r = admin.c.get('/allocation/', query_string={'search': '<script>alert(1)</script>'})  # SEC-03
    assert b'<script>alert(1)</script>' not in r.data
    with app.app_context():
        assert Room.query.count() == 6

    # ---- Student / authorization
    john = Session(app, 'john@student.test', 'student123')
    assert 'Block B' in text(john.c.get(f'/allocation/student/{JOHN}'))  # STUDENT-01
    r = john.c.get(f'/allocation/student/{JANE}', follow_redirects=True)  # STUDENT-02
    assert 'You can only view your own allocation.' in text(r)
    for path in ('/allocation/', '/allocation/create', '/rooms', '/students', f'/allocation/{john_alloc}/reallocate'):  # AUTHZ-03/07/10
        assert 'You do not have permission to access this page.' in text(john.c.get(path, follow_redirects=True)), path
    assert john.c.get('/allocation/available').status_code == 200  # AVAIL-02
    r = john.c.post(f'/allocation/{alloc_id(app, JANE)}/cancel', data=dict(csrf_token=token(john.c, '/')), follow_redirects=True)  # AUTHZ-11
    assert 'permission' in text(r).lower() and alloc_id(app, JANE)
    acct = Session(app, 'accountant@hms.test', 'accountant123')
    assert 'You do not have permission to access this page.' in text(acct.c.get('/allocation/', follow_redirects=True))  # AUTHZ-05

    # ---- DASH-01 / UI-02
    with app.app_context():
        assert Student.query.count() == 6 and Room.query.count() == 6
    dash = soup(admin.c.get('/'))
    card = dash.find(string=lambda s: s and 'Total Students' in s).find_parent(class_=lambda c: c and 'card' in c)
    assert '6' in card.get_text()
    menu = [a.get_text(strip=True) for a in soup(john.c.get('/')).select('.sidebar a.sidebar-link')]
    assert menu == ['Dashboard', 'Available Rooms', 'My Allocation']  # UI-02

    # ---- logout (AUTH-06 / UI-03)
    r = admin.c.post('/auth/logout', data=dict(csrf_token=token(admin.c, '/')), follow_redirects=True)
    assert 'You have been logged out.' in text(r)
    assert 'Please log in to access this page.' in text(admin.c.get('/allocation/', follow_redirects=True))
    assert admin.c.get('/').headers['Cache-Control'] == 'no-store'


def test_sheet_lockout_and_login_page_defaults():
    app = make_app(WTF_CSRF_ENABLED=True, SEED_DEMO_DATA=True, LOGIN_MAX_ATTEMPTS=5)
    c = app.test_client()
    for _ in range(5):  # AUTH-09
        assert 'Invalid email or password.' in text(login(c, 'dana@student.test', 'wrong'))
    r = login(c, 'dana@student.test', 'student123')
    assert r.status_code == 429 and 'Too many failed login attempts. Try again in about 15 minute(s).' in text(r)
    assert login(c, 'john@student.test', 'student123').status_code == 302
    page = text(app.test_client().get('/auth/login'))  # SEC-07
    assert 'admin123' not in page and 'Demo accounts' not in page
