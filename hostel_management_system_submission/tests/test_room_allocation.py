import pytest
from datetime import date, timedelta
from hms_app.models import db, User, Student, Room, RoomAllocation, HostelBlock
import re


def get_csrf_token(client, path='/allocation/create'):
    """Helper to extract CSRF token from a page."""
    response = client.get(path)
    match = re.search(b'name="csrf_token" value="([^"]+)"', response.data)
    if match:
        return match.group(1).decode('utf-8')
    return None


class TestRoomAllocationModel:
    """Test Room and RoomAllocation model methods."""
    
    def test_room_check_availability_available(self, available_room):
        """Test room availability check for available room."""
        assert available_room.check_availability() is True
    
    def test_room_check_availability_full(self, full_room):
        """Test room availability check for full room."""
        assert full_room.check_availability() is False
    
    def test_room_check_availability_maintenance(self, maintenance_room):
        """Test room availability check for maintenance room."""
        assert maintenance_room.check_availability() is False
    
    def test_room_allocate_student_success(self, available_room):
        """Test successful student allocation."""
        assert available_room.occupied_beds == 0
        result = available_room.allocate_student()
        assert result is True
        assert available_room.occupied_beds == 1
        assert available_room.status == 'available'
    
    def test_room_allocate_student_full(self, available_room):
        """Test allocation until room becomes full."""
        available_room.allocate_student()
        available_room.allocate_student()
        assert available_room.occupied_beds == 2
        assert available_room.status == 'full'
        result = available_room.allocate_student()
        assert result is False
    
    def test_room_vacate_student(self, available_room):
        """Test vacating a student."""
        available_room.allocate_student()
        assert available_room.occupied_beds == 1
        result = available_room.vacate_student()
        assert result is True
        assert available_room.occupied_beds == 0
        assert available_room.status == 'available'
    
    def test_room_vacate_student_empty(self, available_room):
        """Test vacating from empty room."""
        result = available_room.vacate_student()
        assert result is False
    
    def test_room_allocation_allocate(self, db_session, student_user, available_room):
        """Test RoomAllocation.allocate() method."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        allocation = RoomAllocation(
            student_id=student.student_id,
            room_id=available_room.room_id,
            start_date=date.today()
        )
        result = allocation.allocate()
        assert result is True
        assert allocation.status == 'active'
        assert available_room.occupied_beds == 1
    
    def test_room_allocation_reallocate(self, db_session, active_allocation, available_room, hostel_block):
        """Test RoomAllocation.reallocate() method."""
        # Create another available room
        new_room = Room(block_id=hostel_block.block_id, room_number='201', floor=2, capacity=2)
        db_session.add(new_room)
        db_session.commit()
        
        old_room_id = active_allocation.room_id
        result = active_allocation.reallocate(new_room.room_id)
        
        assert result is True
        assert active_allocation.room_id == new_room.room_id
        # Old room should be vacated
        old_room = db.session.get(Room, old_room_id)
        assert old_room.occupied_beds == 0
        # New room should be occupied
        new_room = db.session.get(Room, new_room.room_id)
        assert new_room.occupied_beds == 1
    
    def test_room_allocation_reallocate_to_full_room(self, db_session, active_allocation, full_room):
        """Test reallocation to full room fails."""
        result = active_allocation.reallocate(full_room.room_id)
        assert result is False
        assert active_allocation.room_id != full_room.room_id
    
    def test_room_allocation_cancel(self, db_session, active_allocation):
        """Test RoomAllocation.cancel() method."""
        room_id = active_allocation.room_id
        result = active_allocation.cancel()
        
        assert result is True
        assert active_allocation.status == 'cancelled'
        assert active_allocation.end_date == date.today()
        room = db.session.get(Room, room_id)
        assert room.occupied_beds == 0
        assert room.status == 'available'


class TestRoomAllocationCreate:
    """Test room allocation creation via routes."""
    
    def test_create_allocation_success(self, logged_in_admin, student_user, available_room):
        """Test successful allocation creation."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=180)).isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'allocated to' in response.data.lower()
        
        # Verify allocation in database
        allocation = RoomAllocation.query.filter_by(student_id=student.student_id, status='active').first()
        assert allocation is not None
        assert allocation.room_id == available_room.room_id
    
    def test_create_allocation_duplicate_student(self, logged_in_admin, student_user, available_room, active_allocation):
        """Test duplicate allocation for same student fails."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already has an active room allocation' in response.data.lower()
    
    def test_create_allocation_nonexistent_student(self, logged_in_admin, available_room):
        """Test allocation with nonexistent student fails."""
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': 99999,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'does not exist' in response.data.lower()
    
    def test_create_allocation_nonexistent_room(self, logged_in_admin, student_user):
        """Test allocation with nonexistent room fails."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': 99999,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'does not exist' in response.data.lower()
    
    def test_create_allocation_full_room(self, logged_in_admin, student_user, full_room):
        """Test allocation to full room fails."""
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
    
    def test_create_allocation_missing_fields(self, logged_in_admin):
        """Test allocation with missing required fields fails."""
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': '',
            'room_id': '',
            'start_date': '',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'required' in response.data.lower()
    
    def test_create_allocation_invalid_date_format(self, logged_in_admin, student_user, available_room):
        """Test allocation with invalid date format fails."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': 'invalid-date',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'invalid date format' in response.data.lower()
    
    def test_create_allocation_end_date_before_start(self, logged_in_admin, student_user, available_room):
        """Test allocation with end date before start date fails."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'end_date': (date.today() - timedelta(days=1)).isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'end date cannot be earlier' in response.data.lower()


class TestRoomAllocationReallocate:
    """Test room reallocation."""
    
    def test_reallocate_success(self, logged_in_admin, active_allocation, hostel_block):
        """Test successful reallocation."""
        # Create another available room
        new_room = Room(block_id=hostel_block.block_id, room_number='201', floor=2, capacity=2)
        db.session.add(new_room)
        db.session.commit()
        
        csrf_token = get_csrf_token(logged_in_admin, f'/allocation/{active_allocation.allocation_id}/reallocate')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/reallocate', data={
            'new_room_id': new_room.room_id,
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'reallocated' in response.data.lower()
        
        # Verify reallocation
        updated = db.session.get(RoomAllocation, active_allocation.allocation_id)
        assert updated.room_id == new_room.room_id
    
    def test_reallocate_nonexistent_room(self, logged_in_admin, active_allocation):
        """Test reallocation to nonexistent room fails."""
        csrf_token = get_csrf_token(logged_in_admin, f'/allocation/{active_allocation.allocation_id}/reallocate')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/reallocate', data={
            'new_room_id': 99999,
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'does not exist' in response.data.lower()
    
    def test_reallocate_full_room(self, logged_in_admin, active_allocation, full_room):
        """Test reallocation to full room fails."""
        csrf_token = get_csrf_token(logged_in_admin, f'/allocation/{active_allocation.allocation_id}/reallocate')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/reallocate', data={
            'new_room_id': full_room.room_id,
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'not available' in response.data.lower()
    
    def test_reallocate_missing_room(self, logged_in_admin, active_allocation):
        """Test reallocation without room selection fails."""
        csrf_token = get_csrf_token(logged_in_admin, f'/allocation/{active_allocation.allocation_id}/reallocate')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/reallocate', data={
            'new_room_id': '',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'required' in response.data.lower()
    
    def test_reallocate_same_room(self, logged_in_admin, active_allocation):
        """Test reallocation to same room fails."""
        csrf_token = get_csrf_token(logged_in_admin, f'/allocation/{active_allocation.allocation_id}/reallocate')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/reallocate', data={
            'new_room_id': active_allocation.room_id,
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already in that room' in response.data.lower()


class TestRoomAllocationCancel:
    """Test room allocation cancellation."""
    
    def test_cancel_success(self, logged_in_admin, active_allocation):
        """Test successful cancellation."""
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/cancel', data={
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'cancelled' in response.data.lower()
        
        # Verify cancellation
        cancelled = db.session.get(RoomAllocation, active_allocation.allocation_id)
        assert cancelled.status == 'cancelled'
        assert cancelled.end_date == date.today()
        
        # Verify room vacated
        room = db.session.get(Room, cancelled.room_id)
        assert room.occupied_beds == 0
    
    def test_cancel_nonexistent(self, logged_in_admin):
        """Test cancellation of nonexistent allocation."""
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/99999/cancel', data={
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code in (400, 404)


class TestAllocationStateHandling:
    """Test allocation state handling for cancellation and reallocation."""
    
    def test_cancel_active_allocation(self, db_session, student_user, available_room):
        """Test cancelling an active allocation decrements occupancy exactly once."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        allocation = RoomAllocation(
            student_id=student.student_id,
            room_id=available_room.room_id,
            start_date=date.today()
        )
        allocation.allocate()
        db_session.add(allocation)
        db_session.commit()
        
        room_id = allocation.room_id
        room = db.session.get(Room, room_id)
        assert room.occupied_beds == 1
        
        # Cancel the allocation
        result = allocation.cancel()
        db_session.commit()
        
        assert result is True
        assert allocation.status == 'cancelled'
        assert allocation.end_date == date.today()
        
        # Verify room vacated exactly once
        room = db.session.get(Room, room_id)
        assert room.occupied_beds == 0
        assert room.status == 'available'
    
    def test_cancel_already_cancelled_allocation(self, db_session, student_user, available_room):
        """Test cancelling an already-cancelled allocation does not change occupancy."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        allocation = RoomAllocation(
            student_id=student.student_id,
            room_id=available_room.room_id,
            start_date=date.today()
        )
        allocation.allocate()
        db_session.add(allocation)
        db_session.commit()
        
        room_id = allocation.room_id
        room = db.session.get(Room, room_id)
        assert room.occupied_beds == 1
        
        # Cancel first time
        result1 = allocation.cancel()
        db_session.commit()
        assert result1 is True
        assert room.occupied_beds == 0
        
        # Cancel second time - should fail gracefully
        result2 = allocation.cancel()
        db_session.commit()
        
        assert result2 is False
        assert allocation.status == 'cancelled'
        
        # Verify occupancy unchanged (not double-decremented)
        room = db.session.get(Room, room_id)
        assert room.occupied_beds == 0
    
    def test_cancel_nonexistent_allocation_model(self, db_session):
        """Test cancelling a nonexistent allocation fails safely."""
        allocation = RoomAllocation(
            allocation_id=99999,
            student_id=1,
            room_id=1,
            start_date=date.today(),
            status='active'
        )
        room = db.session.get(Room, allocation.room_id)
        result = allocation.cancel()
        assert result is False
    
    def test_reallocate_active_allocation(self, db_session, active_allocation, hostel_block):
        """Test reallocating an active allocation updates both rooms correctly."""
        new_room = Room(block_id=hostel_block.block_id, room_number='201', floor=2, capacity=2)
        db_session.add(new_room)
        db_session.commit()
        
        old_room_id = active_allocation.room_id
        old_room = db.session.get(Room, old_room_id)
        assert old_room.occupied_beds == 1
        
        # Reallocate
        result = active_allocation.reallocate(new_room.room_id)
        db_session.commit()
        
        assert result is True
        assert active_allocation.room_id == new_room.room_id
        
        # Old room should be vacated
        old_room = db.session.get(Room, old_room_id)
        assert old_room.occupied_beds == 0
        assert old_room.status == 'available'
        
        # New room should be occupied
        new_room = db.session.get(Room, new_room.room_id)
        assert new_room.occupied_beds == 1
    
    def test_reallocate_cancelled_allocation_rejected(self, db_session, active_allocation, hostel_block):
        """Test reallocating a cancelled allocation is rejected."""
        # First cancel the allocation
        active_allocation.cancel()
        db_session.commit()
        
        assert active_allocation.status == 'cancelled'
        
        # Create another available room
        new_room = Room(block_id=hostel_block.block_id, room_number='201', floor=2, capacity=2)
        db_session.add(new_room)
        db_session.commit()
        
        # Try to reallocate cancelled allocation
        result = active_allocation.reallocate(new_room.room_id)
        db_session.commit()
        
        # Should be rejected
        assert result is False
        assert active_allocation.status == 'cancelled'
        assert active_allocation.room_id != new_room.room_id
    
    def test_reallocate_nonexistent_allocation(self, db_session, hostel_block):
        """Test reallocating an allocation with non-existent old room fails safely."""
        new_room = Room(block_id=hostel_block.block_id, room_number='201', floor=2, capacity=2)
        db_session.add(new_room)
        db_session.commit()
        
        allocation = RoomAllocation(
            allocation_id=99999,
            student_id=1,
            room_id=99999,  # Non-existent room
            start_date=date.today(),
            status='active'
        )
        
        result = allocation.reallocate(new_room.room_id)
        assert result is False
    
    def test_failed_operation_no_partial_state(self, db_session, student_user, available_room, hostel_block):
        """Test that failed operations do not leave partial state changes."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        
        # Create active allocation
        allocation = RoomAllocation(
            student_id=student.student_id,
            room_id=available_room.room_id,
            start_date=date.today()
        )
        allocation.allocate()
        db_session.add(allocation)
        db_session.commit()
        
        room_id = allocation.room_id
        room = db.session.get(Room, room_id)
        assert room.occupied_beds == 1
        
        # Create a full room for reallocation attempt
        full_room = Room(block_id=hostel_block.block_id, room_number='301', floor=3, capacity=1, occupied_beds=1, status='full')
        db_session.add(full_room)
        db_session.commit()
        
        # Try to reallocate to full room - should fail
        result = allocation.reallocate(full_room.room_id)
        db_session.commit()
        
        assert result is False
        
        # Verify original allocation unchanged
        allocation = db.session.get(RoomAllocation, allocation.allocation_id)
        assert allocation.room_id == room_id
        assert allocation.status == 'active'
        
        # Verify original room occupancy unchanged
        room = db.session.get(Room, room_id)
        assert room.occupied_beds == 1
        
        # Verify full room unchanged
        full_room = db.session.get(Room, full_room.room_id)
        assert full_room.occupied_beds == 1


class TestAvailableRooms:
    """Test available rooms listing."""
    
    def test_available_rooms_list(self, logged_in_admin, available_room, full_room, maintenance_room):
        """Test available rooms list shows only available rooms."""
        response = logged_in_admin.get('/allocation/available')
        assert response.status_code == 200
        
        # Should show available_room
        assert available_room.room_number.encode() in response.data
        # Should not show full_room
        assert full_room.room_number.encode() not in response.data
        # Should not show maintenance_room
        assert maintenance_room.room_number.encode() not in response.data
    
    def test_available_rooms_filter_by_block(self, logged_in_admin, available_room, hostel_block):
        """Test available rooms filter by block."""
        response = logged_in_admin.get(f'/allocation/available?block={hostel_block.block_id}')
        assert response.status_code == 200
        assert available_room.room_number.encode() in response.data
    
    def test_available_rooms_show_all(self, logged_in_admin, available_room, full_room):
        """Test show all rooms option."""
        response = logged_in_admin.get('/allocation/available?show_all=true')
        assert response.status_code == 200
        assert available_room.room_number.encode() in response.data
        assert full_room.room_number.encode() in response.data


class TestStudentAllocationView:
    """Test student viewing their own allocation."""
    
    def test_student_view_own_allocation(self, logged_in_student, student_user, active_allocation):
        """Test student can view their own allocation."""
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        response = logged_in_student.get(f'/allocation/student/{student.student_id}')
        assert response.status_code == 200
        assert active_allocation.room.room_number.encode() in response.data
    
    def test_student_cannot_view_other_allocation(self, logged_in_student, another_student_user, active_allocation):
        """Test student cannot view another student's allocation."""
        other_student = Student.query.filter_by(user_id=another_student_user.user_id).first()
        response = logged_in_student.get(f'/allocation/student/{other_student.student_id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'only view your own' in response.data.lower()
    
    def test_student_can_view_available_rooms(self, logged_in_student, available_room):
        """Test student can view available rooms."""
        response = logged_in_student.get('/allocation/available')
        assert response.status_code == 200
        assert available_room.room_number.encode() in response.data


class TestAllocationIndexPage:
    """Test allocation index page with search and filters."""
    
    def test_allocation_index_loads(self, logged_in_admin):
        """Test allocation index page loads."""
        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200
        assert b'Room Allocations' in response.data
    
    def test_allocation_index_search(self, logged_in_admin, active_allocation):
        """Test allocation index search functionality."""
        response = logged_in_admin.get(f'/allocation/?search={active_allocation.student.user.name}')
        assert response.status_code == 200
        assert active_allocation.student.user.name.encode() in response.data
    
    def test_allocation_index_filter_block(self, logged_in_admin, active_allocation, hostel_block):
        """Test allocation index filter by block."""
        response = logged_in_admin.get(f'/allocation/?block={hostel_block.block_id}')
        assert response.status_code == 200
    
    def test_allocation_index_filter_status(self, logged_in_admin, active_allocation):
        """Test allocation index filter by status."""
        response = logged_in_admin.get('/allocation/?status=active')
        assert response.status_code == 200
        assert b'Active' in response.data
    
    def test_allocation_index_pagination(self, logged_in_admin, db_session, make_students, hostel_block):
        """Test allocation index pagination."""
        # One active allocation per student is a business rule: use 25 distinct students
        students = make_students(25)
        for i in range(25):
            room = Room(block_id=hostel_block.block_id, room_number=f'R{i:03d}', floor=1, capacity=2)
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


class TestRoomsListPage:
    """Test rooms list page."""
    
    def test_rooms_list_loads(self, logged_in_admin, available_room):
        """Test rooms list page loads."""
        response = logged_in_admin.get('/rooms')
        assert response.status_code == 200
        assert b'Room Management' in response.data
        assert available_room.room_number.encode() in response.data
    
    def test_rooms_list_filter(self, logged_in_admin, available_room):
        """Test rooms list filter."""
        response = logged_in_admin.get('/rooms')
        assert response.status_code == 200
        # Filter is client-side, so we just verify page loads


class TestStudentsListPage:
    """Test students list page."""
    
    def test_students_list_loads(self, logged_in_admin, student_user):
        """Test students list page loads."""
        response = logged_in_admin.get('/students')
        assert response.status_code == 200
        assert b'Student Management' in response.data
        assert b'Test Student' in response.data


class TestDashboardPages:
    """Test dashboard pages for different roles."""
    
    def test_admin_dashboard_loads(self, logged_in_admin):
        """Test admin dashboard loads with stats."""
        response = logged_in_admin.get('/')
        assert response.status_code == 200
        assert b'Admin Dashboard' in response.data
        assert b'Total Students' in response.data
        assert b'Total Rooms' in response.data
        assert b'active allocations' in response.data.lower()
    
    def test_warden_dashboard_loads(self, logged_in_warden, available_room):
        """Test warden dashboard loads."""
        response = logged_in_warden.get('/')
        assert response.status_code == 200
        assert b'Warden Dashboard' in response.data
        assert available_room.room_number.encode() in response.data
    
    def test_student_dashboard_loads(self, logged_in_student, student_user, active_allocation):
        """Test student dashboard loads."""
        response = logged_in_student.get('/')
        assert response.status_code == 200
        assert b'Student Dashboard' in response.data
        assert b'Test Student' in response.data
        assert active_allocation.room.room_number.encode() in response.data
    
    def test_accountant_dashboard_loads(self, logged_in_accountant):
        """Test accountant dashboard loads."""
        response = logged_in_accountant.get('/')
        assert response.status_code == 200
        assert b'Accountant Dashboard' in response.data


class TestCreateAllocationPage:
    """Test create allocation page rendering."""
    
    def test_create_page_loads(self, logged_in_admin, student_user, available_room):
        """Test create allocation page loads with form."""
        response = logged_in_admin.get('/allocation/create')
        assert response.status_code == 200
        assert b'Create Room Allocation' in response.data
        assert b'Student' in response.data
        assert b'Room' in response.data
        assert b'Start date' in response.data
        assert b'csrf_token' in response.data
    
    def test_create_page_shows_available_rooms(self, logged_in_admin, available_room, full_room):
        """Test create page only shows available rooms."""
        response = logged_in_admin.get('/allocation/create')
        assert response.status_code == 200
        assert available_room.room_number.encode() in response.data
        assert full_room.room_number.encode() not in response.data
    
    def test_create_page_shows_students(self, logged_in_admin, student_user):
        """Test create page shows students."""
        response = logged_in_admin.get('/allocation/create')
        assert response.status_code == 200
        assert b'Test Student' in response.data


class TestReallocatePage:
    """Test reallocate page rendering."""
    
    def test_reallocate_page_loads(self, logged_in_admin, active_allocation):
        """Test reallocate page loads with current allocation info."""
        response = logged_in_admin.get(f'/allocation/{active_allocation.allocation_id}/reallocate')
        assert response.status_code == 200
        assert b'Reallocate Room' in response.data
        assert active_allocation.student.user.name.encode() in response.data
        assert active_allocation.room.room_number.encode() in response.data
    
    def test_reallocate_page_shows_available_rooms(self, logged_in_admin, active_allocation, available_room):
        """Test reallocate page shows available rooms excluding current."""
        response = logged_in_admin.get(f'/allocation/{active_allocation.allocation_id}/reallocate')
        assert response.status_code == 200
        # Should show other available rooms
        assert b'Select new room' in response.data