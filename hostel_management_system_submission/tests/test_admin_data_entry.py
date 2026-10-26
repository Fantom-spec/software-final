"""Admin data entry: add block / room / student (and the empty-install-to-first-allocation flow)."""
from datetime import date
import pytest
from hms_app.models import db, User, Student, Room, HostelBlock, RoomAllocation
from tests.helpers import make_app, token, login, soup, count_allocations

pytestmark = pytest.mark.ui


def text(resp):
    return soup(resp).get_text(' ', strip=True)


def flash_text(resp):
    return ' '.join(a.get_text(' ', strip=True) for a in soup(resp).select('.alert'))


# ------------------------------------------------------------------ access control
class TestAccess:
    PATHS = ['/blocks/new', '/rooms/new', '/students/new']

    @pytest.mark.parametrize('path', PATHS)
    def test_admin_can_open_forms(self, logged_in_admin, path):
        assert logged_in_admin.get(path).status_code == 200

    @pytest.mark.parametrize('fixture', ['logged_in_warden', 'logged_in_student'])
    @pytest.mark.parametrize('path', PATHS)
    def test_other_roles_are_refused_for_get_and_post(self, request, fixture, path):
        c = request.getfixturevalue(fixture)
        for r in (c.get(path), c.post(path, data={'name': 'x'})):
            assert r.status_code == 302
        assert 'permission' in text(c.get(path, follow_redirects=True)).lower()
        assert HostelBlock.query.count() == 0 and Room.query.count() == 0

    @pytest.mark.parametrize('path', PATHS)
    def test_anonymous_is_sent_to_login(self, client, path):
        assert '/auth/login' in client.get(path).headers['Location']
        assert '/auth/login' in client.post(path, data={}).headers['Location']

    def test_add_buttons_visible_to_admin(self, logged_in_admin):
        a = soup(logged_in_admin.get('/rooms'))
        assert a.select_one('a[href="/rooms/new"]') and a.select_one('a[href="/blocks/new"]')
        assert soup(logged_in_admin.get('/students')).select_one('a[href="/students/new"]')

    def test_add_buttons_hidden_from_warden(self, logged_in_warden):
        w = soup(logged_in_warden.get('/rooms'))
        assert w.select_one('a[href="/rooms/new"]') is None and w.select_one('a[href="/blocks/new"]') is None
        assert soup(logged_in_warden.get('/students')).select_one('a[href="/students/new"]') is None


# ------------------------------------------------------------------ blocks
class TestAddBlock:
    def test_success(self, logged_in_admin):
        r = logged_in_admin.post('/blocks/new', data={'name': ' Block Z ', 'location': 'North'}, follow_redirects=True)
        assert 'Block "Block Z" added.' in flash_text(r)
        b = HostelBlock.query.filter_by(name='Block Z').one()
        assert b.location == 'North'

    def test_location_optional(self, logged_in_admin):
        logged_in_admin.post('/blocks/new', data={'name': 'NoLoc'})
        assert HostelBlock.query.filter_by(name='NoLoc').one().location is None

    @pytest.mark.parametrize('data,msg', [
        ({'name': ''}, 'Block name is required.'),
        ({'name': '   '}, 'Block name is required.'),
        ({'name': 'x' * 51}, 'at most 50 characters'),
        ({'name': 'ok', 'location': 'y' * 201}, 'at most 200 characters'),
    ])
    def test_validation(self, logged_in_admin, data, msg):
        r = logged_in_admin.post('/blocks/new', data=data)
        assert r.status_code == 200 and msg in flash_text(r)
        assert HostelBlock.query.count() == 0

    def test_duplicate_name_rejected_case_insensitively_and_input_kept(self, logged_in_admin, hostel_block):
        r = logged_in_admin.post('/blocks/new', data={'name': hostel_block.name.upper(), 'location': 'kept-loc'})
        assert 'already exists' in flash_text(r)
        assert soup(r).select_one('#location')['value'] == 'kept-loc'
        assert HostelBlock.query.count() == 1


# ------------------------------------------------------------------ rooms
class TestAddRoom:
    def _post(self, c, block, **kw):
        d = dict(block_id=block.block_id, room_number='R1', floor='1', capacity='3', status='available')
        d.update(kw)
        return c.post('/rooms/new', data=d, follow_redirects=True)

    def test_success_and_defaults(self, logged_in_admin, hostel_block):
        r = self._post(logged_in_admin, hostel_block, room_number=' A7 ')
        assert f'Room A7 added to {hostel_block.name}.' in flash_text(r)
        room = Room.query.filter_by(room_number='A7').one()
        assert (room.floor, room.capacity, room.occupied_beds, room.status, room.block_id) == (1, 3, 0, 'available', hostel_block.block_id)

    def test_maintenance_room_is_not_offered_for_allocation(self, logged_in_admin, hostel_block):
        self._post(logged_in_admin, hostel_block, room_number='M1', status='maintenance')
        self._post(logged_in_admin, hostel_block, room_number='OK1')
        offered = [o.get_text() for o in soup(logged_in_admin.get('/allocation/create')).select('#room_id option') if o['value']]
        assert any('OK1' in o for o in offered) and not any('M1' in o for o in offered)

    @pytest.mark.parametrize('kw,msg', [
        ({'room_number': ''}, 'Room number is required.'),
        ({'room_number': 'x' * 21}, 'at most 20 characters'),
        ({'floor': '-1'}, 'Floor must be'), ({'floor': '51'}, 'Floor must be'), ({'floor': 'abc'}, 'Floor must be'), ({'floor': ''}, 'Floor must be'),
        ({'capacity': '0'}, 'Capacity must be'), ({'capacity': '11'}, 'Capacity must be'), ({'capacity': 'x'}, 'Capacity must be'),
        ({'status': 'full'}, 'Status must be'), ({'status': 'haunted'}, 'Status must be'),
        ({'block_id': '99999'}, 'choose an existing block'), ({'block_id': ''}, 'choose an existing block'),
    ])
    def test_validation_rejects_and_creates_nothing(self, logged_in_admin, hostel_block, kw, msg):
        r = self._post(logged_in_admin, hostel_block, **kw)
        assert r.status_code == 200 and msg in flash_text(r)
        assert Room.query.count() == 0

    def test_boundaries_are_accepted(self, logged_in_admin, hostel_block):
        assert 'added' in flash_text(self._post(logged_in_admin, hostel_block, room_number='lo', floor='0', capacity='1'))
        assert 'added' in flash_text(self._post(logged_in_admin, hostel_block, room_number='hi', floor='50', capacity='10'))
        assert Room.query.count() == 2

    def test_duplicate_in_same_block_rejected_but_same_number_in_other_block_ok(self, logged_in_admin, hostel_block, db_session):
        self._post(logged_in_admin, hostel_block, room_number='D1')
        assert 'already exists' in flash_text(self._post(logged_in_admin, hostel_block, room_number='d1'))
        other = HostelBlock(name='Other Block')
        db_session.add(other)
        db_session.commit()
        assert 'added' in flash_text(self._post(logged_in_admin, other, room_number='D1'))
        assert Room.query.count() == 2

    def test_input_kept_on_error(self, logged_in_admin, hostel_block):
        s = soup(self._post(logged_in_admin, hostel_block, room_number='KEEP', capacity='99'))
        assert s.select_one('#room_number')['value'] == 'KEEP'
        assert s.select_one('#block_id option[selected]')['value'] == str(hostel_block.block_id)

    def test_without_blocks_the_form_explains_and_blocks_submission(self, logged_in_admin):
        s = soup(logged_in_admin.get('/rooms/new'))
        assert 'no blocks yet' in s.get_text().lower() and s.select_one('a[href="/blocks/new"]')
        assert s.select_one('form.needs-validation button[type=submit]').has_attr('disabled')


# ------------------------------------------------------------------ students
class TestAddStudent:
    GOOD = dict(name='Eve Adams', email='Eve@Student.Test', roll_no='ST-100', course='B.Tech', batch='2025',
                password='Str0ngPass!', confirm_password='Str0ngPass!')

    def _post(self, c, **kw):
        d = dict(self.GOOD); d.update(kw)
        return c.post('/students/new', data=d, follow_redirects=True)

    def test_success_creates_student_user_and_profile(self, logged_in_admin):
        r = self._post(logged_in_admin)
        assert 'Student Eve Adams (ST-100) added.' in flash_text(r)
        u = User.query.filter_by(email='eve@student.test').one()          # e-mail normalised to lower case
        assert u.role == 'student' and u.password_hash != 'Str0ngPass!' and u.check_password('Str0ngPass!')
        s = Student.query.filter_by(user_id=u.user_id).one()
        assert (s.roll_no, s.course, s.batch) == ('ST-100', 'B.Tech', '2025')
        assert 'Eve Adams' in text(logged_in_admin.get('/students'))

    def test_optional_fields_may_be_empty(self, logged_in_admin):
        self._post(logged_in_admin, course='', batch='')
        s = Student.query.filter_by(roll_no='ST-100').one()
        assert s.course is None and s.batch is None

    def test_new_student_can_log_in(self):
        app = make_app(WTF_CSRF_ENABLED=True)
        with app.app_context():
            a = User(name='A', email='a@t.test', role='admin'); a.set_password('Admin#12345'); db.session.add(a); db.session.commit()
        c = app.test_client()
        assert login(c, 'a@t.test', 'Admin#12345').status_code == 302
        d = dict(TestAddStudent.GOOD, csrf_token=token(c, '/students/new'))
        assert c.post('/students/new', data=d).status_code == 302
        s = app.test_client()
        assert login(s, 'eve@student.test', 'Str0ngPass!').status_code == 302
        assert 'Eve Adams' in text(s.get('/'))

    @pytest.mark.parametrize('kw,msg', [
        ({'name': ''}, 'Name is required.'), ({'name': 'n' * 101}, 'at most 100'),
        ({'email': ''}, 'valid e-mail'), ({'email': 'not-an-email'}, 'valid e-mail'), ({'email': 'a@b'}, 'valid e-mail'), ({'email': 'a b@c.de'}, 'valid e-mail'),
        ({'roll_no': ''}, 'Roll number is required'), ({'roll_no': 'bad roll!'}, 'Roll number is required'), ({'roll_no': 'r' * 21}, 'Roll number is required'),
        ({'course': 'c' * 101}, 'Course must be'), ({'batch': 'b' * 21}, 'Batch must be'),
        ({'password': 'short', 'confirm_password': 'short'}, 'Password must be'),
        ({'password': 'p' * 129, 'confirm_password': 'p' * 129}, 'Password must be'),
        ({'confirm_password': 'Different1!'}, 'do not match'),
    ])
    def test_validation_rejects_and_creates_nothing(self, logged_in_admin, kw, msg):
        users_before = User.query.count()      # includes the logged-in admin
        r = self._post(logged_in_admin, **kw)
        assert r.status_code == 200 and msg in flash_text(r)
        assert User.query.count() == users_before and Student.query.count() == 0

    def test_duplicate_email_and_roll_number_rejected_case_insensitively(self, logged_in_admin):
        self._post(logged_in_admin)
        assert 'already exists' in flash_text(self._post(logged_in_admin, email='EVE@student.test', roll_no='OTHER-1'))
        assert 'already in use' in flash_text(self._post(logged_in_admin, email='new@student.test', roll_no='st-100'))
        assert Student.query.count() == 1

    def test_passwords_are_never_echoed_back(self, logged_in_admin):
        r = self._post(logged_in_admin, confirm_password='mismatch!!')
        s = soup(r)
        assert s.select_one('#name')['value'] == 'Eve Adams'               # other input kept
        assert not s.select_one('#password').get('value') and not s.select_one('#confirm_password').get('value')
        assert 'Str0ngPass!' not in r.get_data(as_text=True)

    def test_hostile_name_is_escaped_on_the_list(self, logged_in_admin):
        self._post(logged_in_admin, name='<script>alert(1)</script>')
        r = logged_in_admin.get('/students')
        assert b'<script>alert(1)</script>' not in r.data and b'&lt;script&gt;' in r.data


# ------------------------------------------------------------------ CSRF (protection ON)
class TestCsrf:
    @pytest.fixture
    def env(self):
        app = make_app(WTF_CSRF_ENABLED=True)
        with app.app_context():
            a = User(name='A', email='a@t.test', role='admin'); a.set_password('Admin#12345')
            db.session.add_all([a, HostelBlock(name='B1')]); db.session.commit()
        c = app.test_client()
        assert login(c, 'a@t.test', 'Admin#12345').status_code == 302
        return app, c

    @pytest.mark.parametrize('path,data', [
        ('/blocks/new', {'name': 'NewBlock'}),
        ('/rooms/new', {'block_id': '1', 'room_number': 'X1', 'floor': '1', 'capacity': '2'}),
        ('/students/new', dict(TestAddStudent.GOOD)),
    ])
    def test_forms_reject_missing_and_forged_tokens_and_accept_valid(self, env, path, data):
        app, c = env
        def counts():
            with app.app_context():
                return HostelBlock.query.count(), Room.query.count(), Student.query.count()
        before = counts()
        assert c.post(path, data=data).status_code == 400
        assert c.post(path, data=dict(data, csrf_token='forged')).status_code == 400
        assert counts() == before
        assert c.post(path, data=dict(data, csrf_token=token(c, path))).status_code == 302
        assert counts() != before


# ------------------------------------------------------------------ the empty-install flow
def test_empty_install_to_first_allocation_end_to_end():
    """What a fresh deployment needs: create-admin, then add data through the UI, then allocate."""
    app = make_app(WTF_CSRF_ENABLED=True)
    with app.app_context():
        res = app.test_cli_runner().invoke(args=['create-admin', '--name', 'Root', '--email', 'root@x.test', '--password', 'R00t#Passw0rd'])
        assert res.exit_code == 0, res.output
    c = app.test_client()
    assert login(c, 'root@x.test', 'R00t#Passw0rd').status_code == 302

    def post(path, **d):
        return c.post(path, data=dict(d, csrf_token=token(c, path)), follow_redirects=True)

    assert 'added' in flash_text(post('/blocks/new', name='North', location='Campus'))
    with app.app_context():
        block_id = HostelBlock.query.one().block_id
    assert 'added' in flash_text(post('/rooms/new', block_id=block_id, room_number='101', floor=1, capacity=2, status='available'))
    assert 'added' in flash_text(post('/students/new', **TestAddStudent.GOOD))
    with app.app_context():
        sid, rid = Student.query.one().student_id, Room.query.one().room_id
    r = post('/allocation/create', student_id=sid, room_id=rid, start_date=date.today().isoformat())
    assert 'Room 101 allocated to Eve Adams successfully.' in flash_text(r)
    assert count_allocations(app, status='active') == 1
    stu = app.test_client()
    assert login(stu, 'eve@student.test', 'Str0ngPass!').status_code == 302
    assert 'North' in text(stu.get(f'/allocation/student/{sid}')) and '101' in text(stu.get(f'/allocation/student/{sid}'))
