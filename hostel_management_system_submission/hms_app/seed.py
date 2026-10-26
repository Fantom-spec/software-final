"""Opt-in demo data and admin bootstrap.

Nothing here runs automatically. Enable demo data with HMS_SEED_DEMO_DATA=1 or
the `seed-demo` CLI command. The demo accounts use well-known passwords and must
never be enabled on a real deployment.
"""
from datetime import date
from hms_app.models import (db, User, Student, Room, RoomAllocation, HostelBlock,
                            Warden, Admin, Accountant)

DEMO_ACCOUNTS = [
    ('Admin', 'admin@hms.test', 'admin123'),
    ('Warden', 'warden@hms.test', 'warden123'),
    ('Student', 'john@student.test', 'student123'),
    ('Accountant', 'accountant@hms.test', 'accountant123'),
]


def create_admin_user(name, email, password):
    if User.query.filter(db.func.lower(User.email) == email.lower()).first():
        raise ValueError(f'A user with e-mail {email} already exists.')
    user = User(name=name, email=email.lower(), role='admin')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(Admin(user_id=user.user_id, designation='System Administrator'))
    db.session.commit()
    return user


def seed_demo_data():
    """Create demo users, blocks and rooms. Returns False if data already exists."""
    if User.query.first():
        return False

    admin_user = User(name='Admin User', email='admin@hms.test', role='admin')
    admin_user.set_password('admin123')
    db.session.add(admin_user)
    db.session.flush()
    db.session.add(Admin(user_id=admin_user.user_id, designation='System Administrator'))

    warden_user = User(name='Warden Smith', email='warden@hms.test', role='warden')
    warden_user.set_password('warden123')
    db.session.add(warden_user)
    db.session.flush()
    db.session.add(Warden(user_id=warden_user.user_id, department='Boys Hostel Block A'))

    for name, email, roll_no, course, batch in [
        ('John Doe', 'john@student.test', 'STU001', 'B.Tech CSE', '2023'),
        ('Jane Smith', 'jane@student.test', 'STU002', 'B.Tech ECE', '2023'),
        ('Bob Wilson', 'bob@student.test', 'STU003', 'B.Tech ME', '2022'),
        ('Alice Brown', 'alice@student.test', 'STU004', 'B.Tech IT', '2024'),
        ('Carlos Diaz', 'carlos@student.test', 'STU005', 'B.Tech CSE', '2024'),
        ('Dana Evans', 'dana@student.test', 'STU006', 'B.Tech ECE', '2022'),
    ]:
        user = User(name=name, email=email, role='student')
        user.set_password('student123')
        db.session.add(user)
        db.session.flush()
        db.session.add(Student(user_id=user.user_id, roll_no=roll_no, course=course, batch=batch))

    acc_user = User(name='Accountant Brown', email='accountant@hms.test', role='accountant')
    acc_user.set_password('accountant123')
    db.session.add(acc_user)
    db.session.flush()
    db.session.add(Accountant(user_id=acc_user.user_id, designation='Fee Accountant'))

    block_a = HostelBlock(name='Block A', location='Main Campus')
    block_b = HostelBlock(name='Block B', location='East Campus')
    db.session.add_all([block_a, block_b])
    db.session.flush()
    for block_id, room_num, floor, cap in [
        (block_a.block_id, '101', 1, 2), (block_a.block_id, '102', 1, 2),
        (block_a.block_id, '201', 2, 2), (block_a.block_id, '202', 2, 2),
        (block_b.block_id, '101', 1, 3), (block_b.block_id, '102', 1, 3),
    ]:
        db.session.add(Room(block_id=block_id, room_number=room_num, floor=floor, capacity=cap))
    db.session.commit()
    return True


def seed_demo_allocations():
    """Allocate the demo students through the real model logic (for demos/screenshots)."""
    created = 0
    rooms = {(r.block.name, r.room_number): r for r in Room.query.all()}
    plan = [('STU001', ('Block A', '101')), ('STU002', ('Block A', '101')), ('STU003', ('Block B', '101'))]
    for roll_no, key in plan:
        student = Student.query.filter_by(roll_no=roll_no).first()
        room = rooms.get(key)
        if not student or not room or RoomAllocation.has_active_allocation(student.student_id):
            continue
        alloc = RoomAllocation(student_id=student.student_id, room_id=room.room_id, start_date=date.today())
        if alloc.allocate():
            db.session.add(alloc)
            created += 1
    db.session.commit()
    return created
