import sys
import os
import pytest
from datetime import date, timedelta

# Make the project root importable regardless of where pytest is launched from
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from hms_app import create_app
from hms_app.models import db, User, Student, Room, RoomAllocation, HostelBlock, Warden, Admin, Accountant
from hms_app.config import TestConfig


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing."""
    with app.app_context():
        # Clear all tables
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        
        yield db.session
        
        # Cleanup
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture(scope='function')
def admin_user(db_session):
    """Create admin user."""
    user = User(name='Test Admin', email='admin@test.com', role='admin')
    user.set_password('admin123')
    db_session.add(user)
    db_session.flush()
    admin = Admin(user_id=user.user_id, designation='Test Admin')
    db_session.add(admin)
    db_session.commit()
    return user


@pytest.fixture(scope='function')
def warden_user(db_session):
    """Create warden user."""
    user = User(name='Test Warden', email='warden@test.com', role='warden')
    user.set_password('warden123')
    db_session.add(user)
    db_session.flush()
    warden = Warden(user_id=user.user_id, department='Test Block')
    db_session.add(warden)
    db_session.commit()
    return user


@pytest.fixture(scope='function')
def student_user(db_session):
    """Create student user."""
    user = User(name='Test Student', email='student@test.com', role='student')
    user.set_password('student123')
    db_session.add(user)
    db_session.flush()
    student = Student(user_id=user.user_id, roll_no='TEST001', course='B.Tech', batch='2024')
    db_session.add(student)
    db_session.commit()
    return user


@pytest.fixture(scope='function')
def make_students(db_session):
    """Factory: create n distinct students (each with their own user account)."""
    def _make(n, prefix='BULK'):
        students = []
        for i in range(n):
            user = User(name=f'{prefix} Student {i}', email=f'{prefix.lower()}{i}@test.com', role='student')
            user.set_password('student123')
            db_session.add(user)
            db_session.flush()
            student = Student(user_id=user.user_id, roll_no=f'{prefix}{i:03d}', course='B.Tech', batch='2024')
            db_session.add(student)
            students.append(student)
        db_session.commit()
        return students
    return _make


@pytest.fixture(scope='function')
def another_student_user(db_session):
    """Create another student user."""
    user = User(name='Another Student', email='student2@test.com', role='student')
    user.set_password('student123')
    db_session.add(user)
    db_session.flush()
    student = Student(user_id=user.user_id, roll_no='TEST002', course='B.Tech', batch='2024')
    db_session.add(student)
    db_session.commit()
    return user


@pytest.fixture(scope='function')
def accountant_user(db_session):
    """Create accountant user."""
    user = User(name='Test Accountant', email='accountant@test.com', role='accountant')
    user.set_password('accountant123')
    db_session.add(user)
    db_session.flush()
    acc = Accountant(user_id=user.user_id, designation='Test Accountant')
    db_session.add(acc)
    db_session.commit()
    return user


@pytest.fixture(scope='function')
def hostel_block(db_session):
    """Create hostel block."""
    block = HostelBlock(name='Test Block', location='Test Location')
    db_session.add(block)
    db_session.commit()
    return block


@pytest.fixture(scope='function')
def available_room(db_session, hostel_block):
    """Create an available room."""
    room = Room(block_id=hostel_block.block_id, room_number='101', floor=1, capacity=2)
    db_session.add(room)
    db_session.commit()
    return room


@pytest.fixture(scope='function')
def full_room(db_session, hostel_block):
    """Create a full room."""
    room = Room(block_id=hostel_block.block_id, room_number='102', floor=1, capacity=2, occupied_beds=2, status='full')
    db_session.add(room)
    db_session.commit()
    return room


@pytest.fixture(scope='function')
def maintenance_room(db_session, hostel_block):
    """Create a room under maintenance."""
    room = Room(block_id=hostel_block.block_id, room_number='103', floor=1, capacity=2, status='maintenance')
    db_session.add(room)
    db_session.commit()
    return room


def _login_user(client, email, password):
    """Helper to log in a user."""
    response = client.get('/auth/login')
    csrf_token = None
    import re
    match = re.search(b'name="csrf_token" value="([^"]+)"', response.data)
    if match:
        csrf_token = match.group(1).decode('utf-8')
    
    login_data = {
        'email': email,
        'password': password
    }
    if csrf_token:
        login_data['csrf_token'] = csrf_token
    
    client.post('/auth/login', data=login_data, follow_redirects=True)
    return client


@pytest.fixture(scope='function')
def logged_in_admin(client, admin_user):
    """Log in as admin."""
    return _login_user(client, 'admin@test.com', 'admin123')


@pytest.fixture(scope='function')
def logged_in_warden(client, warden_user):
    """Log in as warden."""
    return _login_user(client, 'warden@test.com', 'warden123')


@pytest.fixture(scope='function')
def logged_in_student(client, student_user):
    """Log in as student."""
    return _login_user(client, 'student@test.com', 'student123')


@pytest.fixture(scope='function')
def logged_in_accountant(client, accountant_user):
    """Log in as accountant."""
    return _login_user(client, 'accountant@test.com', 'accountant123')


@pytest.fixture(scope='function')
def active_allocation(db_session, student_user, available_room):
    """Create an active room allocation."""
    student = Student.query.filter_by(user_id=student_user.user_id).first()
    allocation = RoomAllocation(
        student_id=student.student_id,
        room_id=available_room.room_id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=180)
    )
    allocation.allocate()
    db_session.add(allocation)
    db_session.commit()
    return allocation


@pytest.fixture(scope='function')
def csrf_token_getter(client):
    """Fixture to get CSRF token from a page."""
    def _get_csrf_token(path='/allocation/create'):
        response = client.get(path)
        import re
        match = re.search(b'name="csrf_token" value="([^"]+)"', response.data)
        if match:
            return match.group(1).decode('utf-8')
        return None
    return _get_csrf_token