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
        old_room = Room.query.get(old_room_id)
        assert old_room.occupied_beds == 0
        # New room should be occupied
        new_room = Room.query.get(new_room.room_id)
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
        room = Room.query.get(room_id)
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
        updated = RoomAllocation.query.get(active_allocation.allocation_id)
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


class TestRoomAllocationCancel:
    """Test room allocation cancellation."""
    
    def test_cancel_success(self, logged_in_admin, active_allocation):
        """Test successful cancellation."""
        # GET the index page to get CSRF token (cancel is POST from index)
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/')
        response = logged_in_admin.post(f'/allocation/{active_allocation.allocation_id}/cancel', data={
            'csrf_token': csrf_token
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'cancelled' in response.data.lower()
        
        # Verify cancellation
        cancelled = RoomAllocation.query.get(active_allocation.allocation_id)
        assert cancelled.status == 'cancelled'
        assert cancelled.end_date == date.today()
        
        # Verify room vacated
        room = Room.query.get(cancelled.room_id)
        assert room.occupied_beds == 0
    
    def test_cancel_nonexistent(self, logged_in_admin):
        """Test cancellation of nonexistent allocation."""
        # Get CSRF token from create page (always has a form)
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/99999/cancel', data={
            'csrf_token': csrf_token
        }, follow_redirects=True)
        # CSRF validation happens before route handler, so valid token -> 404, invalid -> 400
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
        room = Room.query.get(room_id)
        assert room.occupied_beds == 1
        
        # Cancel the allocation
        result = allocation.cancel()
        db_session.commit()
        
        assert result is True
        assert allocation.status == 'cancelled'
        assert allocation.end_date == date.today()
        
        # Verify room vacated exactly once
        room = Room.query.get(room_id)
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
        room = Room.query.get(room_id)
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
        room = Room.query.get(room_id)
        assert room.occupied_beds == 0
    
    def test_cancel_nonexistent_allocation_model(self, db_session):
        """Test cancelling a nonexistent allocation fails safely."""
        # Try to cancel non-existent allocation by creating one with invalid ID
        allocation = RoomAllocation(
            allocation_id=99999,
            student_id=1,
            room_id=1,
            start_date=date.today(),
            status='active'
        )
        # Don't add to session, just test the method
        room = Room.query.get(allocation.room_id)
        # Since room doesn't exist, cancel should return False
        result = allocation.cancel()
        assert result is False
    
    def test_reallocate_active_allocation(self, db_session, active_allocation, hostel_block):
        """Test reallocating an active allocation updates both rooms correctly."""
        # Create another available room
        new_room = Room(block_id=hostel_block.block_id, room_number='201', floor=2, capacity=2)
        db_session.add(new_room)
        db_session.commit()
        
        old_room_id = active_allocation.room_id
        old_room = Room.query.get(old_room_id)
        assert old_room.occupied_beds == 1
        
        # Reallocate
        result = active_allocation.reallocate(new_room.room_id)
        db_session.commit()
        
        assert result is True
        assert active_allocation.room_id == new_room.room_id
        
        # Old room should be vacated
        old_room = Room.query.get(old_room_id)
        assert old_room.occupied_beds == 0
        assert old_room.status == 'available'
        
        # New room should be occupied
        new_room = Room.query.get(new_room.room_id)
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
        
        # Use a room_id that definitely doesn't exist
        allocation = RoomAllocation(
            allocation_id=99999,
            student_id=1,
            room_id=99999,  # Non-existent room
            start_date=date.today(),
            status='active'
        )
        
        result = allocation.reallocate(new_room.room_id)
        # Should fail because old room doesn't exist
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
        room = Room.query.get(room_id)
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
        allocation = RoomAllocation.query.get(allocation.allocation_id)
        assert allocation.room_id == room_id
        assert allocation.status == 'active'
        
        # Verify original room occupancy unchanged
        room = Room.query.get(room_id)
        assert room.occupied_beds == 1
        
        # Verify full room unchanged
        full_room = Room.query.get(full_room.room_id)
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