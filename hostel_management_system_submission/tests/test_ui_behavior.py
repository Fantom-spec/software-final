"""UI behavior verified by parsing the rendered DOM (not by searching for substrings)."""
from datetime import date
import pytest
from hms_app.models import db, Student, Room, RoomAllocation
from tests.helpers import soup

pytestmark = pytest.mark.ui


def nav(resp):
    """{label: href} for the sidebar links."""
    s = soup(resp)
    return {a.get_text(strip=True): a['href'] for a in s.select('nav.sidebar a.sidebar-link, .sidebar a.sidebar-link')}


class TestRoleBasedNavigation:
    def test_admin_menu(self, logged_in_admin):
        links = nav(logged_in_admin.get('/'))
        assert list(links) == ['Dashboard', 'Allocations', 'Available Rooms', 'Rooms', 'Students']
        assert links['Allocations'] == '/allocation/' and links['Rooms'] == '/rooms' and links['Students'] == '/students'

    def test_warden_menu_same_as_admin(self, logged_in_warden):
        assert list(nav(logged_in_warden.get('/'))) == ['Dashboard', 'Allocations', 'Available Rooms', 'Rooms', 'Students']

    def test_student_menu_has_no_staff_pages(self, logged_in_student, student_user):
        links = nav(logged_in_student.get('/'))
        assert list(links) == ['Dashboard', 'Available Rooms', 'My Allocation']
        sid = Student.query.filter_by(user_id=student_user.user_id).first().student_id
        assert links['My Allocation'] == f'/allocation/student/{sid}'

    def test_admin_never_sees_my_allocation(self, logged_in_admin):
        for path in ('/', '/allocation/', '/rooms', '/students', '/allocation/available'):
            assert 'My Allocation' not in nav(logged_in_admin.get(path)), path

    def test_my_allocation_link_leads_to_own_allocation(self, logged_in_student, student_user, active_allocation):
        href = nav(logged_in_student.get('/'))['My Allocation']
        r = logged_in_student.get(href)
        assert r.status_code == 200
        assert active_allocation.room.room_number in soup(r).find('main').get_text()

    def test_student_cannot_open_staff_pages(self, logged_in_student):
        for path in ('/allocation/', '/allocation/create', '/rooms', '/students'):
            r = logged_in_student.get(path)
            assert r.status_code == 302 and r.headers['Location'].endswith('/'), path

    def test_active_menu_item_marked(self, logged_in_admin):
        s = soup(logged_in_admin.get('/rooms'))
        active = [a.get_text(strip=True) for a in s.select('.sidebar a.sidebar-link.active')]
        assert active == ['Rooms']


class TestSingleLogoutControl:
    @pytest.mark.parametrize('fixture', ['logged_in_admin', 'logged_in_warden', 'logged_in_student'])
    def test_exactly_one_post_logout_form(self, request, fixture):
        client = request.getfixturevalue(fixture)
        for path in ('/', '/allocation/available'):
            s = soup(client.get(path))
            forms = s.select('form[action="/auth/logout"]')
            assert len(forms) == 1, path
            assert forms[0]['method'].lower() == 'post'
            assert forms[0].select_one('input[name=csrf_token]')['value']
            assert [a for a in s.find_all('a', href=True) if 'logout' in a['href']] == []
            assert len([e for e in s.find_all(['a', 'button']) if 'logout' in e.get_text().lower()]) == 1

    def test_top_bar_has_no_logout(self, logged_in_admin):
        top = soup(logged_in_admin.get('/')).select_one('header.top-bar')
        assert 'logout' not in top.get_text().lower()

    def test_logout_form_works(self, logged_in_admin):
        r = logged_in_admin.post('/auth/logout', follow_redirects=True)
        assert 'logged out' in soup(r).select_one('.alert').get_text().lower()
        assert logged_in_admin.get('/').status_code == 302


class TestForms:
    def test_create_form_controls_are_labelled_and_required_where_needed(self, logged_in_admin):
        form = soup(logged_in_admin.get('/allocation/create')).select_one('form[method=POST]')
        controls = form.select('select, input:not([type=hidden])')
        assert {c['id'] for c in controls} == {'student_id', 'room_id', 'start_date', 'end_date'}
        for c in controls:
            assert form.select_one(f'label[for="{c["id"]}"]'), f'no <label for> for {c["id"]}'
        required = {c['id'] for c in controls if c.has_attr('required')}
        assert required == {'student_id', 'room_id', 'start_date'}
        assert form.select_one('input[name=csrf_token]')['value']
        assert form.select_one('button[type=submit]')

    def test_create_form_only_offers_assignable_rooms(self, logged_in_admin, available_room, full_room, maintenance_room):
        values = [o['value'] for o in soup(logged_in_admin.get('/allocation/create')).select('#room_id option') if o['value']]
        assert values == [str(available_room.room_id)]

    def test_login_form_controls(self, client):
        s = soup(client.get('/auth/login'))
        assert s.select_one('input#email[type=email][required]')
        assert s.select_one('input#password[type=password][required]')
        assert s.select_one('label[for=email]') and s.select_one('label[for=password]')
        assert s.select_one('button#togglePw[aria-label]')

    def test_cancel_is_post_with_confirmation_and_token(self, logged_in_admin, active_allocation):
        form = soup(logged_in_admin.get('/allocation/')).select_one(f'form[action$="/{active_allocation.allocation_id}/cancel"]')
        assert form['method'].upper() == 'POST'
        assert form['data-confirm'].strip()
        assert form.select_one('input[name=csrf_token]')['value']


class TestConfirmationModal:
    def test_modal_present_for_authenticated_users_only(self, logged_in_admin, client):
        s = soup(logged_in_admin.get('/allocation/'))
        modal = s.select_one('#confirmModal[aria-labelledby]')
        assert modal and modal.select_one('#confirmModalMessage') and modal.select_one('#confirmModalOk')
        assert modal.select_one('[data-bs-dismiss=modal].btn-outline-secondary')       # "Go back"
        assert soup(client.get('/auth/login')).select_one('#confirmModal') is None

    def test_native_confirm_is_gone(self, logged_in_admin):
        assert 'confirm(' not in logged_in_admin.get('/allocation/').get_data(as_text=True).replace('data-confirm(', '')


class TestFeedback:
    def test_success_message_is_a_visible_alert(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        r = logged_in_admin.post('/allocation/create', data=dict(student_id=student.student_id, room_id=available_room.room_id,
                                                                  start_date=date.today().isoformat()), follow_redirects=True)
        alert = soup(r).select_one('.alert-success[role=alert]')
        assert alert and 'allocated' in alert.get_text().lower()

    def test_messages_render_at_top_of_page_content_not_after_the_layout(self, logged_in_admin, student_user, available_room):
        """Regression: flashes were emitted after the whole layout (below the fold, easy to miss)."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        r = logged_in_admin.post('/allocation/create', data=dict(student_id=student.student_id, room_id=available_room.room_id,
                                                                  start_date=date.today().isoformat()), follow_redirects=True)
        s = soup(r)
        alert = s.select_one('main.main-content .page-content .flash-region .alert-success')
        assert alert is not None
        assert [a for a in s.select('.alert') if a.find_parent('main') is None] == []   # none stranded outside <main>
        page = s.select_one('.page-content')
        first_block = next(c for c in page.find_all(recursive=False) if c.name and 'flash-region' not in c.get('class', []))
        assert page.find_all(recursive=False).index(alert.find_parent(class_='flash-region')) < page.find_all(recursive=False).index(first_block)

    def test_error_message_is_an_error_alert(self, logged_in_admin, student_user, available_room, active_allocation):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        r = logged_in_admin.post('/allocation/create', data=dict(student_id=student.student_id, room_id=available_room.room_id,
                                                                  start_date=date.today().isoformat()), follow_redirects=True)
        alert = soup(r).select_one('.alert-error, .alert-danger')
        assert alert and 'already has an active' in alert.get_text()


class TestNoLeakedMarkup:
    def test_no_literal_html_entities_in_visible_text(self, logged_in_admin, db_session, student_user, available_room):
        """Regression: '&mdash;' used inside a Jinja expression was shown literally in the End column."""
        st = Student.query.filter_by(user_id=student_user.user_id).first()
        a = RoomAllocation(student_id=st.student_id, room_id=available_room.room_id, start_date=date.today(), end_date=None)
        assert a.allocate()
        db_session.add(a)
        db_session.commit()  # open-ended allocation: the End column renders the placeholder
        for path in ('/', '/allocation/', '/allocation/available', '/rooms', '/students'):
            text = soup(logged_in_admin.get(path)).get_text(' ')
            assert not __import__('re').search(r'&[a-z]+;|&#\d+;', text), path

    def test_open_ended_allocation_shows_dash_in_end_column(self, logged_in_admin, db_session, student_user, available_room):
        st = Student.query.filter_by(user_id=student_user.user_id).first()
        a = RoomAllocation(student_id=st.student_id, room_id=available_room.room_id, start_date=date.today(), end_date=None)
        assert a.allocate()
        db_session.add(a)
        db_session.commit()
        row = soup(logged_in_admin.get('/allocation/')).select('table tbody tr')[0]
        assert row.select('td')[6].get_text(strip=True) == '—'


class TestListBehavior:
    def _rows(self, resp):
        return soup(resp).select('table tbody tr')

    def test_search_filters_rows(self, logged_in_admin, db_session, make_students, hostel_block):
        studs = make_students(3, prefix='ZZ')
        for i, st in enumerate(studs):
            room = Room(block_id=hostel_block.block_id, room_number=f'F{i}', floor=1, capacity=2)
            db_session.add(room)
            db_session.flush()
            a = RoomAllocation(student_id=st.student_id, room_id=room.room_id, start_date=date.today())
            a.allocate()
            db_session.add(a)
        db_session.commit()
        assert len(self._rows(logged_in_admin.get('/allocation/'))) == 3
        rows = self._rows(logged_in_admin.get('/allocation/?search=ZZ%20Student%201'))
        assert len(rows) == 1 and 'ZZ Student 1' in rows[0].get_text()
        assert 'No allocations found' in soup(logged_in_admin.get('/allocation/?search=nobody-matches')).find('main').get_text()

    def test_status_filter_separates_active_and_cancelled(self, logged_in_admin, db_session, student_user, available_room):
        st = Student.query.filter_by(user_id=student_user.user_id).first()
        a = RoomAllocation(student_id=st.student_id, room_id=available_room.room_id, start_date=date.today())
        a.allocate()
        db_session.add(a)
        db_session.commit()
        assert len(self._rows(logged_in_admin.get('/allocation/?status=active'))) == 1
        assert 'No allocations found' in soup(logged_in_admin.get('/allocation/?status=cancelled')).find('main').get_text()
        a.cancel()
        db_session.commit()
        assert 'No allocations found' in soup(logged_in_admin.get('/allocation/?status=active')).find('main').get_text()
        assert len(self._rows(logged_in_admin.get('/allocation/?status=cancelled'))) == 1

    def test_pagination_shows_20_then_remainder(self, logged_in_admin, db_session, make_students, hostel_block):
        studs = make_students(25, prefix='PG')
        for i, st in enumerate(studs):
            room = Room(block_id=hostel_block.block_id, room_number=f'G{i:02d}', floor=1, capacity=2)
            db_session.add(room)
            db_session.flush()
            a = RoomAllocation(student_id=st.student_id, room_id=room.room_id, start_date=date.today())
            a.allocate()
            db_session.add(a)
        db_session.commit()
        p1, p2 = logged_in_admin.get('/allocation/'), logged_in_admin.get('/allocation/?page=2')
        assert len(self._rows(p1)) == 20 and len(self._rows(p2)) == 5
        assert soup(p1).select_one('.pagination a.page-link[href*="page=2"]')
        assert logged_in_admin.get('/allocation/?page=0').status_code == 200
        assert logged_in_admin.get('/allocation/?page=999').status_code == 200


class TestAccessibilityAndResponsiveMarkup:
    def test_viewport_meta(self, client):
        meta = soup(client.get('/auth/login')).find('meta', attrs={'name': 'viewport'})
        assert 'width=device-width' in meta['content'] and 'initial-scale=1' in meta['content']

    def test_mobile_toggle_is_an_accessible_button_hidden_on_desktop(self, logged_in_admin):
        btn = soup(logged_in_admin.get('/')).select_one('button#sidebarToggle')
        assert btn['aria-label'] and 'd-lg-none' in btn['class']

    def test_progressbar_is_fully_described(self, logged_in_admin):
        bar = soup(logged_in_admin.get('/')).select_one('[role=progressbar]')
        assert bar['aria-label'] and bar['aria-valuemin'] == '0' and bar['aria-valuemax'] == '100' and bar['aria-valuenow'].isdigit()

    def test_search_input_has_accessible_name(self, logged_in_admin):
        assert soup(logged_in_admin.get('/allocation/')).select_one('input[type=search][aria-label]')

    def test_css_defines_focus_and_layout_fixes(self, client):
        css = client.get('/static/css/hms.css').get_data(as_text=True)
        assert ':focus-visible' in css
        assert '.main-content { min-width: 0; }' in css          # prevents flex overflow on mobile
        assert 'padding-left: 4.5rem' in css                       # room for the hamburger beside the title

    def test_breadcrumb_trail_is_correct(self, logged_in_admin):
        crumbs = [li.get_text(strip=True) for li in soup(logged_in_admin.get('/allocation/create')).select('ol.breadcrumb li')]
        assert crumbs == ['Dashboard', 'Allocations', 'Create']
