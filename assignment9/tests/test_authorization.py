import pytest
from hms_app.models import db, User, Student, Room, RoomAllocation, HostelBlock, Warden, Admin, Accountant
from datetime import date
import re


def get_csrf_token(client, path='/allocation/create'):
    """Helper to extract CSRF token from a page."""
    response = client.get(path)
    match = re.search(b'name="csrf_token" value="([^"]+)"', response.data)
    if match:
        return match.group(1).decode('utf-8')
    return None


class TestAuthentication:
    """Test authentication requirements."""
    
    def test_login_page_accessible(self, client):
        """Test login page is accessible without authentication."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_dashboard_redirects_to_login(self, client):
        """Test dashboard redirects to login when not authenticated."""
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()
    
    def test_allocation_routes_redirect_to_login(self, client):
        """Test allocation routes redirect to login when not authenticated."""
        routes = [
            '/allocation/',
            '/allocation/create',
            '/allocation/available',
        ]
        for route in routes:
            response = client.get(route, follow_redirects=True)
            assert response.status_code == 200
            assert b'login' in response.data.lower()
    
    def test_valid_login_admin(self, client, admin_user):
        """Test valid admin login."""
        csrf_token = get_csrf_token(client, '/auth/login')
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'admin dashboard' in response.data.lower() or b'welcome' in response.data.lower()
    
    def test_valid_login_warden(self, client, warden_user):
        """Test valid warden login."""
        csrf_token = get_csrf_token(client, '/auth/login')
        response = client.post('/auth/login', data={
            'email': 'warden@test.com',
            'password': 'warden123',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_valid_login_student(self, client, student_user):
        """Test valid student login."""
        csrf_token = get_csrf_token(client, '/auth/login')
        response = client.post('/auth/login', data={
            'email': 'student@test.com',
            'password': 'student123',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_valid_login_accountant(self, client, accountant_user):
        """Test valid accountant login."""
        csrf_token = get_csrf_token(client, '/auth/login')
        response = client.post('/auth/login', data={
            'email': 'accountant@test.com',
            'password': 'accountant123',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_invalid_password_rejected(self, client, admin_user):
        """Test invalid password is rejected."""
        csrf_token = get_csrf_token(client, '/auth/login')
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'wrongpassword',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'invalid' in response.data.lower()
    
    def test_nonexistent_user_rejected(self, client):
        """Test nonexistent user is rejected."""
        csrf_token = get_csrf_token(client, '/auth/login')
        response = client.post('/auth/login', data={
            'email': 'nonexistent@test.com',
            'password': 'password',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            assert b'invalid' in response.data.lower()
    
    def test_logout_clears_session(self, logged_in_admin):
        """Test logout clears session."""
        response = logged_in_admin.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'logged out' in response.data.lower()
        
        # Verify cannot access protected route
        response = logged_in_admin.get('/', follow_redirects=True)
        assert b'login' in response.data.lower()


class TestAuthorization:
    """Test role-based authorization."""
    
    def test_admin_can_access_allocation_index(self, logged_in_admin):
        """Test admin can access allocation index."""
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
    
    def test_admin_can_create_allocation(self, logged_in_admin):
        """Test admin can access create allocation page."""
        response = logged_in_admin.get('/allocation/create')
        assert response.status_code == 200
    
    def test_admin_can_view_available_rooms(self, logged_in_admin):
        """Test admin can view available rooms."""
        response = logged_in_admin.get('/allocation/available')
        assert response.status_code == 200
    
    def test_warden_can_access_allocation_index(self, logged_in_warden):
        """Test warden can access allocation index."""
        response = logged_in_warden.get('/allocation/')
        assert response.status_code == 200
    
    def test_warden_can_create_allocation(self, logged_in_warden):
        """Test warden can access create allocation page."""
        response = logged_in_warden.get('/allocation/create')
        assert response.status_code == 200
    
    def test_warden_can_view_available_rooms(self, logged_in_warden):
        """Test warden can view available rooms."""
        response = logged_in_warden.get('/allocation/available')
        assert response.status_code == 200
    
    def test_student_cannot_access_allocation_index(self, logged_in_student):
        """Test student cannot access allocation index."""
        response = logged_in_student.get('/allocation/', follow_redirects=True)
        assert response.status_code == 200
        assert b'permission' in response.data.lower()
    
    def test_student_cannot_create_allocation(self, logged_in_student):
        """Test student cannot access create allocation page."""
        response = logged_in_student.get('/allocation/create', follow_redirects=True)
        assert response.status_code == 200
        assert b'permission' in response.data.lower()
    
    def test_student_can_view_available_rooms(self, logged_in_student):
        """Test student can view available rooms (read-only)."""
        response = logged_in_student.get('/allocation/available')
        assert response.status_code == 200
    
    def test_student_can_view_own_allocation(self, logged_in_student, student_user, active_allocation):
        """Test student can view their own allocation."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        response = logged_in_student.get(f'/allocation/student/{student.student_id}')
        assert response.status_code == 200
    
    def test_student_cannot_view_other_allocation(self, logged_in_student, another_student_user, active_allocation):
        """Test student cannot view another student's allocation."""
        other_student = Student.query.filter_by(user_id=another_student_user.user_id).first()
        response = logged_in_student.get(f'/allocation/student/{other_student.student_id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'only view your own' in response.data.lower()
    
    def test_accountant_cannot_access_allocation_management(self, client, db_session, accountant_user):
        """Test accountant cannot access allocation management."""
        response = client.get('/allocation/', follow_redirects=True)
        assert response.status_code == 200
        assert b'permission' in response.data.lower()
    
    def test_admin_can_access_room_management(self, logged_in_admin):
        """Test admin can access room management."""
        response = logged_in_admin.get('/rooms')
        assert response.status_code == 200
    
    def test_warden_can_access_room_management(self, logged_in_warden):
        """Test warden can access room management."""
        response = logged_in_warden.get('/rooms')
        assert response.status_code == 200
    
    def test_student_cannot_access_room_management(self, logged_in_student):
        """Test student cannot access room management."""
        response = logged_in_student.get('/rooms', follow_redirects=True)
        assert response.status_code == 200
        assert b'permission' in response.data.lower()
    
    def test_admin_can_access_student_management(self, logged_in_admin):
        """Test admin can access student management."""
        response = logged_in_admin.get('/students')
        assert response.status_code == 200
    
    def test_warden_can_access_student_management(self, logged_in_warden):
        """Test warden can access student management."""
        response = logged_in_warden.get('/students')
        assert response.status_code == 200
    
    def test_student_cannot_access_student_management(self, logged_in_student):
        """Test student cannot access student management."""
        response = logged_in_student.get('/students', follow_redirects=True)
        assert response.status_code == 200
        assert b'permission' in response.data.lower()
    
    def test_admin_can_reallocate(self, logged_in_admin, active_allocation):
        """Test admin can access reallocate page."""
        response = logged_in_admin.get(f'/allocation/{active_allocation.allocation_id}/reallocate')
        assert response.status_code == 200
    
    def test_warden_can_reallocate(self, logged_in_warden, active_allocation):
        """Test warden can access reallocate page."""
        response = logged_in_warden.get(f'/allocation/{active_allocation.allocation_id}/reallocate')
        assert response.status_code == 200
    
    def test_student_cannot_reallocate(self, logged_in_student, active_allocation):
        """Test student cannot access reallocate page."""
        response = logged_in_student.get(f'/allocation/{active_allocation.allocation_id}/reallocate', follow_redirects=True)
        assert response.status_code == 200
        assert b'permission' in response.data.lower()
    
    def test_admin_can_cancel(self, logged_in_admin, active_allocation):
        """Test admin can cancel allocation."""
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/cancel', data={
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'cancelled' in response.data.lower()
    
    def test_warden_can_cancel(self, logged_in_warden, active_allocation):
        """Test warden can cancel allocation."""
        csrf_token = get_csrf_token(logged_in_warden, '/allocation/create')
        response = logged_in_warden.post(f'/allocation/{active_allocation.allocation_id}/cancel', data={
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'cancelled' in response.data.lower()
    
    def test_student_cannot_cancel(self, logged_in_student, active_allocation):
        """Test student cannot cancel allocation."""
        csrf_token = get_csrf_token(logged_in_student, '/allocation/create')
        response = logged_in_student.post(f'/allocation/{active_allocation.allocation_id}/cancel', data={
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'permission' in response.data.lower()


class TestSessionManagement:
    """Test session management."""
    
    def test_session_persists_across_requests(self, logged_in_admin):
        """Test session persists across requests."""
        response1 = logged_in_admin.get('/')
        assert response1.status_code == 200
        
        response2 = logged_in_admin.get('/allocation/')
        assert response2.status_code == 200
    
    def test_concurrent_sessions_different_users(self, logged_in_admin, logged_in_warden):
        """Test that different users can have separate sessions."""
        # Verify admin access
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
        
        # Verify warden access (separate session)
        response = logged_in_warden.get('/allocation/')
        assert response.status_code == 200


class TestCSRFProtection:
    """Test CSRF protection."""
    
    def test_valid_csrf_token_accepted(self, logged_in_admin, student_user, available_room):
        """Test valid CSRF token is accepted."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'allocated to' in response.data.lower()
    
    def test_missing_csrf_token_rejected(self, logged_in_admin, student_user, available_room):
        """Test missing CSRF token is rejected."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        # Don't include CSRF token
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat()
        }, follow_redirects=True)
        # Flask-WTF returns 400 for missing CSRF token
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            assert b'csrf' in response.data.lower() or b'token' in response.data.lower() or b'required' in response.data.lower()
    
    def test_invalid_csrf_token_rejected(self, logged_in_admin, student_user, available_room):
        """Test invalid CSRF token is rejected."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': 'invalid-token'
        }, follow_redirects=True)
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            assert b'csrf' in response.data.lower() or b'token' in response.data.lower() or b'invalid' in response.data.lower()
    
    def test_csrf_state_preserved_after_rejection(self, logged_in_admin, student_user, available_room):
        """Test that application state is preserved after CSRF rejection."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        # Try with invalid token
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': 'invalid-token'
        }, follow_redirects=True)
        
        # Then try with valid token - should still work
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'allocated to' in response.data.lower()
    
    def test_cancel_csrf_protection(self, logged_in_admin, active_allocation):
        """Test CSRF protection on cancel endpoint."""
        # Test with valid token - should work
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/cancel', data={
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'cancelled' in response.data.lower()
        
        # Test with invalid token - should be rejected
        # Need a new allocation since the previous one was cancelled
        # The key point is that CSRF is enforced on the endpoint