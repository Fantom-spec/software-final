import pytest
from bs4 import BeautifulSoup
from hms_app.models import db, User, Student, Room, RoomAllocation, HostelBlock
from datetime import date
import re


def get_csrf_token(client, path='/auth/login'):
    """Helper to extract CSRF token from a page."""
    response = client.get(path)
    match = re.search(b'name="csrf_token" value="([^"]+)"', response.data)
    if match:
        return match.group(1).decode('utf-8')
    return None


class TestUIRendering:
    """Test UI page rendering and elements."""
    
    def test_login_page_elements(self, client):
        """Test login page has all required elements."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'csrf_token' in response.data
        assert b'email' in response.data
        assert b'password' in response.data
        assert b'Login' in response.data
        assert b'Hostel Management System' in response.data
    
    def test_admin_dashboard_elements(self, logged_in_admin):
        """Test admin dashboard has all required UI elements."""
        response = logged_in_admin.get('/')
        assert response.status_code == 200
        # Check for stat cards
        assert b'Total Students' in response.data
        assert b'Total Rooms' in response.data
        assert b'Occupied Rooms' in response.data
        assert b'Available Rooms' in response.data
        # Check for quick actions
        assert b'Allocate Room' in response.data
        assert b'View All Allocations' in response.data
        assert b'Available Rooms' in response.data
        # Check for bed occupancy progress
        assert b'Bed Occupancy' in response.data or b'Bed occupancy' in response.data
        # Check for recent allocations table
        assert b'Recent Allocations' in response.data
    
    def test_warden_dashboard_elements(self, logged_in_warden, available_room):
        """Test warden dashboard has all required UI elements."""
        response = logged_in_warden.get('/')
        assert response.status_code == 200
        assert b'Warden Dashboard' in response.data
        assert b'Room Status' in response.data
        assert available_room.room_number.encode() in response.data
        assert b'New Allocation' in response.data
    
    def test_student_dashboard_elements(self, logged_in_student, student_user, active_allocation):
        """Test student dashboard has all required UI elements."""
        response = logged_in_student.get('/')
        assert response.status_code == 200
        assert b'Student Dashboard' in response.data
        assert b'Profile' in response.data
        assert b'Room Allocation' in response.data
        assert active_allocation.room.room_number.encode() in response.data
        assert b'View Details' in response.data
    
    def test_allocation_index_elements(self, logged_in_admin, active_allocation):
        """Test allocation index page has all required UI elements."""
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
        assert b'Room Allocations' in response.data
        assert b'New Allocation' in response.data
        # Check for search and filter
        assert b'Search' in response.data or b'search' in response.data
        assert b'Block' in response.data
        assert b'Status' in response.data
        # Check for table headers
        assert b'Student' in response.data
        assert b'Roll No' in response.data
        assert b'Room' in response.data
        assert b'Block' in response.data
        assert b'Actions' in response.data
        # Check for action buttons
        assert b'Reallocate' in response.data or b'bi-arrow-left-right' in response.data
        assert b'Cancel' in response.data or b'bi-x-lg' in response.data
    
    def test_create_allocation_page_elements(self, logged_in_admin):
        """Test create allocation page has all required UI elements."""
        response = logged_in_admin.get('/allocation/create')
        assert response.status_code == 200
        assert b'Create Room Allocation' in response.data
        # Form fields
        assert b'Student' in response.data
        assert b'Room' in response.data
        assert b'Start date' in response.data
        assert b'End date' in response.data
        # Required field indicators
        assert b'*' in response.data
        # CSRF token
        assert b'csrf_token' in response.data
        # Buttons
        assert b'Create allocation' in response.data
        assert b'Cancel' in response.data
    
    def test_reallocate_page_elements(self, logged_in_admin, active_allocation):
        """Test reallocate page has all required UI elements."""
        response = logged_in_admin.get(f'/allocation/{active_allocation.allocation_id}/reallocate')
        assert response.status_code == 200
        assert b'Reallocate Room' in response.data
        assert b'Current Allocation' in response.data
        assert b'New room' in response.data
        assert active_allocation.student.user.name.encode() in response.data
        assert active_allocation.room.room_number.encode() in response.data
        assert b'Reallocate' in response.data
    
    def test_available_rooms_page_elements(self, logged_in_admin, available_room):
        """Test available rooms page has all required UI elements."""
        response = logged_in_admin.get('/allocation/available')
        assert response.status_code == 200
        assert b'Available Rooms' in response.data
        assert available_room.room_number.encode() in response.data
        # Check table columns
        assert b'Room' in response.data
        assert b'Block' in response.data
        assert b'Floor' in response.data
        assert b'Capacity' in response.data
        assert b'Occupancy' in response.data
        assert b'Free beds' in response.data
        assert b'Status' in response.data
        # Filter
        assert b'Block' in response.data
        assert b'Show full rooms' in response.data
    
    def test_student_allocation_view_elements(self, logged_in_student, student_user, active_allocation):
        """Test student allocation view has all required UI elements."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        response = logged_in_student.get(f'/allocation/student/{student.student_id}')
        assert response.status_code == 200
        assert b'Room Allocation' in response.data
        assert active_allocation.room.room_number.encode() in response.data
        assert active_allocation.room.block.name.encode() in response.data
        assert b'Allocated on' in response.data
        assert b'Start date' in response.data
        assert b'Status' in response.data
    
    def test_rooms_list_elements(self, logged_in_admin, available_room):
        """Test rooms list page has all required elements."""
        response = logged_in_admin.get('/rooms')
        assert response.status_code == 200
        assert b'Room Management' in response.data
        assert b'Filter rooms' in response.data
        assert available_room.room_number.encode() in response.data
    
    def test_students_list_elements(self, logged_in_admin, student_user):
        """Test students list page has all required elements."""
        response = logged_in_admin.get('/students')
        assert response.status_code == 200
        assert b'Student Management' in response.data
        assert b'Filter students' in response.data
        assert b'Test Student' in response.data
        assert b'Allocation' in response.data


class TestResponsiveLayout:
    """Test responsive layout elements."""
    
    def test_base_template_has_viewport(self, client):
        """Test base template has viewport meta tag."""
        response = client.get('/auth/login')
        assert b'viewport' in response.data
        assert b'width=device-width' in response.data
    
    def test_sidebar_navigation_present(self, logged_in_admin):
        """Sidebar exposes exactly the admin destinations, each pointing at the right URL."""
        response = logged_in_admin.get('/')
        assert response.status_code == 200
        links = {a.get_text(strip=True): a['href'] for a in BeautifulSoup(response.data, 'html.parser').select('.sidebar a.sidebar-link')}
        assert links == {'Dashboard': '/', 'Allocations': '/allocation/', 'Available Rooms': '/allocation/available',
                         'Rooms': '/rooms', 'Students': '/students'}
        assert BeautifulSoup(response.data, 'html.parser').select('form[action="/auth/logout"] button')

    def test_mobile_sidebar_toggle(self, logged_in_admin):
        """Toggle is an accessible <button>, shown below the lg breakpoint only."""
        response = logged_in_admin.get('/')
        btn = BeautifulSoup(response.data, 'html.parser').select_one('button#sidebarToggle')
        assert btn is not None and btn.get('aria-label') and 'd-lg-none' in btn['class']

    def test_breadcrumb_navigation(self, logged_in_admin):
        """Test breadcrumb navigation on pages."""
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
        assert b'breadcrumb' in response.data.lower()
        assert b'Dashboard' in response.data
        assert b'Allocations' in response.data


class TestFlashMessages:
    """Test flash message display."""
    
    def test_success_flash_message(self, logged_in_admin, student_user, available_room):
        """Test success flash message appears after allocation."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'alert-success' in response.data or b'alert' in response.data
        assert b'allocated' in response.data.lower()
    
    def test_error_flash_message(self, logged_in_admin, student_user, available_room, active_allocation):
        """Test error flash message appears for duplicate allocation."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'alert-danger' in response.data or b'alert' in response.data
        assert b'already has an active' in response.data.lower()
    
    def test_warning_flash_message(self, logged_in_admin, full_room, student_user):
        """Test warning/error flash for full room."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': full_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'not available' in response.data.lower()


class TestFormValidation:
    """Test form validation UI."""
    
    def test_create_form_html5_validation(self, logged_in_admin):
        """Test create form has HTML5 validation attributes."""
        response = logged_in_admin.get('/allocation/create')
        assert response.status_code == 200
        assert b'required' in response.data
        assert b'min=' in response.data  # Date min attribute
    
    def test_create_form_client_side_validation(self, logged_in_admin):
        """Test create form has client-side validation script."""
        response = logged_in_admin.get('/allocation/create')
        assert response.status_code == 200
        assert b'was-validated' in response.data or b'needs-validation' in response.data
        assert b'addEventListener' in response.data
    
    def test_reallocate_form_validation(self, logged_in_admin, active_allocation):
        """Test reallocate form has validation."""
        response = logged_in_admin.get(f'/allocation/{active_allocation.allocation_id}/reallocate')
        assert response.status_code == 200
        assert b'required' in response.data
        assert b'needs-validation' in response.data


class TestAccessibility:
    """Test accessibility features."""
    
    def test_form_labels_associated(self, logged_in_admin):
        """Every visible form control has a <label for> pointing at its id."""
        response = logged_in_admin.get('/allocation/create')
        assert response.status_code == 200
        s = BeautifulSoup(response.data, 'html.parser')
        controls = s.select('form select, form input:not([type=hidden])')
        assert controls
        for c in controls:
            assert s.select_one(f'label[for="{c["id"]}"]'), c.get('id')

    def test_aria_labels_present(self, logged_in_admin):
        """The search box and pagination landmarks have accessible names."""
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
        s = BeautifulSoup(response.data, 'html.parser')
        assert s.select_one('input[type=search]').get('aria-label')
        assert s.select_one('nav[aria-label="breadcrumb"]')

    def test_role_attributes(self, logged_in_admin):
        """The occupancy bar is a fully described progressbar."""
        response = logged_in_admin.get('/')
        assert response.status_code == 200
        bar = BeautifulSoup(response.data, 'html.parser').select_one('[role=progressbar]')
        assert bar['aria-label'] and bar['aria-valuemin'] == '0' and bar['aria-valuemax'] == '100'
        assert 0 <= int(bar['aria-valuenow']) <= 100

    def test_focus_indicators(self, client):
        """The stylesheet is linked, served, and defines visible keyboard focus styles."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        href = BeautifulSoup(response.data, 'html.parser').select_one('link[href*="hms.css"]')['href']
        css = client.get(href)
        assert css.status_code == 200 and ':focus-visible' in css.get_data(as_text=True)

class TestNavigation:
    """Test navigation flow between pages."""
    
    def test_admin_nav_to_allocations(self, logged_in_admin):
        """Test admin can navigate to allocations from dashboard."""
        response = logged_in_admin.get('/')
        assert response.status_code == 200
        assert b'/allocation/' in response.data
    
    def test_admin_nav_to_rooms(self, logged_in_admin):
        """Test admin can navigate to rooms from dashboard."""
        response = logged_in_admin.get('/')
        assert response.status_code == 200
        assert b'/rooms' in response.data
    
    def test_admin_nav_to_students(self, logged_in_admin):
        """Test admin can navigate to students from dashboard."""
        response = logged_in_admin.get('/')
        assert response.status_code == 200
        assert b'/students' in response.data
    
    def test_student_nav_to_available(self, logged_in_student):
        """Test student can navigate to available rooms."""
        response = logged_in_student.get('/')
        assert response.status_code == 200
        assert b'/allocation/available' in response.data
    
    def test_student_nav_to_my_allocation(self, logged_in_student, student_user):
        """Test student can navigate to their allocation."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        response = logged_in_student.get('/')
        assert response.status_code == 200
        # Link should be present
        assert b'/allocation/student/' in response.data


class TestEmptyStates:
    """Test empty state handling."""
    
    def test_empty_allocations_state(self, logged_in_admin, db_session):
        """Test empty state when no allocations exist."""
        # Clear all allocations
        for alloc in RoomAllocation.query.all():
            db_session.delete(alloc)
        db_session.commit()
        
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
        assert b'No allocations found' in response.data or b'No active allocations' in response.data
    
    def test_empty_rooms_state(self, logged_in_admin, db_session):
        """Test empty state when no rooms exist."""
        # Clear all rooms
        for room in Room.query.all():
            db_session.delete(room)
        db_session.commit()
        
        response = logged_in_admin.get('/rooms')
        assert response.status_code == 200
        assert b'No rooms found' in response.data
    
    def test_empty_available_rooms_state(self, logged_in_admin, db_session):
        """Test empty state when no available rooms."""
        # Make all rooms full
        for room in Room.query.all():
            room.occupied_beds = room.capacity
            room.status = 'full'
        db_session.commit()
        
        response = logged_in_admin.get('/allocation/available')
        assert response.status_code == 200
        assert b'No available rooms' in response.data


class TestConfirmationPrompts:
    """Test confirmation prompts for destructive actions."""
    
    def test_cancel_has_confirmation(self, logged_in_admin, active_allocation):
        """Cancel is a POST form guarded by a confirmation message and a CSRF token."""
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
        form = BeautifulSoup(response.data, 'html.parser').select_one('form[data-confirm]')
        assert form['method'].upper() == 'POST' and form['data-confirm'].strip()
        assert form.select_one('input[name=csrf_token]')['value']

class TestPagination:
    """Test pagination functionality."""
    
    def test_allocation_pagination(self, logged_in_admin, db_session, make_students, hostel_block):
        """Test allocation pagination works."""
        # One active allocation per student is a business rule: use 25 distinct students
        students = make_students(25)
        for i in range(25):
            room = Room(block_id=hostel_block.block_id, room_number=f'P{i:03d}', floor=1, capacity=2)
            db_session.add(room)
            db_session.flush()
            alloc = RoomAllocation(
                student_id=students[i].student_id,
                room_id=room.room_id,
                start_date=date.today(),
                status='active'
            )
            alloc.allocate()
            db_session.add(alloc)
        db_session.commit()
        
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
        assert b'pagination' in response.data.lower() or b'page' in response.data.lower()
        assert b'Previous' in response.data or b'Next' in response.data
        assert b'Showing' in response.data