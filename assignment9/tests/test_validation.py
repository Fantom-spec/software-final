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


class TestInputValidation:
    """Test input validation for room allocation forms."""

    def test_empty_student_id_rejected(self, logged_in_admin, available_room):
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': '',
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'required' in response.data.lower()

    def test_empty_room_id_rejected(self, logged_in_admin, student_user):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': '',
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'required' in response.data.lower()

    def test_empty_start_date_rejected(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': '',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'required' in response.data.lower()

    def test_invalid_student_id_type_rejected(self, logged_in_admin, available_room):
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': 'abc',
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_invalid_room_id_type_rejected(self, logged_in_admin, student_user):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': 'xyz',
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_past_start_date_accepted(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        past_date = date.today().replace(year=date.today().year - 1)
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': past_date.isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_end_date_before_start_date_rejected(self, logged_in_admin, student_user, available_room):
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

    def test_sql_injection_student_id(self, logged_in_admin, available_room):
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': "1 OR 1=1",
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        allocations = RoomAllocation.query.all()
        for alloc in allocations:
            assert alloc.student_id != "1 OR 1=1"

    def test_sql_injection_room_id(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': "1; DROP TABLE rooms",
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        rooms = Room.query.all()
        assert len(rooms) > 0

    def test_sql_injection_rollback_verification(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        initial_count = RoomAllocation.query.count()
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': "1; DELETE FROM room_allocations",
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)
        assert response.status_code == 200
        final_count = RoomAllocation.query.count()
        assert final_count == initial_count

    def test_xss_in_form_fields(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()

        allocation = RoomAllocation(
            student_id=student.student_id,
            room_id=available_room.room_id,
            start_date=date.today()
        )
        allocation.allocate()
        db.session.add(allocation)
        db.session.commit()

        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')

        student.user.name = '<script>alert(1)</script>'
        db.session.commit()

        response = logged_in_admin.get('/allocation/')
        assert response.status_code == 200

        payload = '<script>alert(1)</script>'
        assert payload.encode() not in response.data
        # Verify HTML-escaped version IS in response
        assert b'script' in response.data
        assert b'alert(1)' in response.data
        assert b'/script' in response.data

    def test_xss_in_student_name_display(self, db_session, logged_in_admin, available_room):
        user = User(name='<script>alert("xss")</script>', email='xss@test.com', role='student')
        user.set_password('pass')
        db_session.add(user)
        db_session.flush()
        student = Student(user_id=user.user_id, roll_no='XSS001', course='B.Tech', batch='2024')
        db_session.add(student)
        db_session.commit()

        csrf_token = get_csrf_token(logged_in_admin, '/allocation/create')
        response = logged_in_admin.post('/allocation/create', data={
            'student_id': student.student_id,
            'room_id': available_room.room_id,
            'start_date': date.today().isoformat(),
            'csrf_token': csrf_token
        }, follow_redirects=True)

        assert response.status_code == 200
        payload = '<script>alert("xss")</script>'
        assert payload.encode() not in response.data
        # Verify HTML-escaped version IS in response
        assert b'script' in response.data
        assert b'alert(' in response.data
        assert b'xss' in response.data
        assert b'/script' in response.data


class TestDatabaseConstraints:
    def test_user_email_unique(self, db_session):
        user1 = User(name='User 1', email='unique@test.com', role='student')
        user1.set_password('pass')
        db_session.add(user1)
        db_session.commit()
        user2 = User(name='User 2', email='unique@test.com', role='student')
        user2.set_password('pass')
        db_session.add(user2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_student_roll_no_unique(self, db_session):
        user1 = User(name='User 1', email='user1@test.com', role='student')
        user1.set_password('pass')
        db_session.add(user1)
        db_session.flush()
        student1 = Student(user_id=user1.user_id, roll_no='UNIQUE001', course='B.Tech', batch='2024')
        db_session.add(student1)
        db_session.commit()
        user2 = User(name='User 2', email='user2@test.com', role='student')
        user2.set_password('pass')
        db_session.add(user2)
        db_session.flush()
        student2 = Student(user_id=user2.user_id, roll_no='UNIQUE001', course='B.Tech', batch='2024')
        db_session.add(student2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_room_number_unique_per_block(self, db_session, hostel_block):
        room1 = Room(block_id=hostel_block.block_id, room_number='101', floor=1, capacity=2)
        db_session.add(room1)
        db_session.commit()
        room2 = Room(block_id=hostel_block.block_id, room_number='101', floor=2, capacity=2)
        db_session.add(room2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_foreign_key_student_allocation(self, db_session, hostel_block):
        room = Room(block_id=hostel_block.block_id, room_number='101', floor=1, capacity=2)
        db_session.add(room)
        db_session.commit()
        allocation = RoomAllocation(student_id=99999, room_id=room.room_id, start_date=date.today())
        db_session.add(allocation)
        with pytest.raises(Exception):
            db_session.commit()

    def test_foreign_key_room_allocation(self, db_session, student_user):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        allocation = RoomAllocation(student_id=student.student_id, room_id=99999, start_date=date.today())
        db_session.add(allocation)
        with pytest.raises(Exception):
            db_session.commit()


class TestBusinessLogicValidation:
    def test_student_one_active_allocation(self, db_session, student_user, available_room, hostel_block):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        alloc1 = RoomAllocation(student_id=student.student_id, room_id=available_room.room_id, start_date=date.today())
        alloc1.allocate()
        db_session.add(alloc1)
        db_session.commit()
        room2 = Room(block_id=hostel_block.block_id, room_number='102', floor=1, capacity=2)
        db_session.add(room2)
        db_session.commit()
        alloc2 = RoomAllocation(student_id=student.student_id, room_id=room2.room_id, start_date=date.today())
        result2 = alloc2.allocate()
        assert result2 is False
        assert alloc2.status != 'active'
        active_count = RoomAllocation.query.filter_by(student_id=student.student_id, status='active').count()
        assert active_count == 1

    def test_cancelled_allocation_allows_new_allocation(self, db_session, student_user, available_room, hostel_block):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        alloc1 = RoomAllocation(student_id=student.student_id, room_id=available_room.room_id, start_date=date.today())
        alloc1.allocate()
        db_session.add(alloc1)
        db_session.commit()
        alloc1.cancel()
        db_session.commit()
        assert alloc1.status == 'cancelled'
        room2 = Room(block_id=hostel_block.block_id, room_number='102', floor=1, capacity=2)
        db_session.add(room2)
        db_session.commit()
        alloc2 = RoomAllocation(student_id=student.student_id, room_id=room2.room_id, start_date=date.today())
        result2 = alloc2.allocate()
        db_session.add(alloc2)
        db_session.commit()
        assert result2 is True
        assert alloc2.status == 'active'
        active_count = RoomAllocation.query.filter_by(student_id=student.student_id, status='active').count()
        assert active_count == 1

    def test_room_capacity_not_exceeded_via_model(self, db_session, student_user, available_room, another_student_user, hostel_block):
        student1 = Student.query.filter_by(user_id=student_user.user_id).first()
        student2 = Student.query.filter_by(user_id=another_student_user.user_id).first()
        alloc1 = RoomAllocation(student_id=student1.student_id, room_id=available_room.room_id, start_date=date.today())
        alloc1.allocate()
        db_session.add(alloc1)
        alloc2 = RoomAllocation(student_id=student2.student_id, room_id=available_room.room_id, start_date=date.today())
        alloc2.allocate()
        db_session.add(alloc2)
        db_session.commit()
        user3 = User(name='Student 3', email='student3@test.com', role='student')
        user3.set_password('pass')
        db_session.add(user3)
        db_session.flush()
        student3 = Student(user_id=user3.user_id, roll_no='TEST003', course='B.Tech', batch='2024')
        db_session.add(student3)
        db_session.commit()
        alloc3 = RoomAllocation(student_id=student3.student_id, room_id=available_room.room_id, start_date=date.today())
        result = alloc3.allocate()
        assert result is False
        assert available_room.occupied_beds == 2