from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import case, update, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timezone

db = SQLAlchemy()


def _utcnow():
    """Naive UTC timestamp (replaces the deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'warden', 'student', 'accountant'
    created_at = db.Column(db.DateTime, default=_utcnow)

    # Relationships
    student_profile = db.relationship('Student', back_populates='user', uselist=False, cascade='all, delete-orphan')
    warden = db.relationship('Warden', backref='user', uselist=False, cascade='all, delete-orphan')
    admin = db.relationship('Admin', backref='user', uselist=False, cascade='all, delete-orphan')
    accountant = db.relationship('Accountant', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_warden(self):
        return self.role == 'warden'

    def is_student(self):
        return self.role == 'student'

    def is_accountant(self):
        return self.role == 'accountant'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Admin(db.Model):
    __tablename__ = 'admins'

    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    designation = db.Column(db.String(100))


class Warden(db.Model):
    __tablename__ = 'wardens'

    warden_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    department = db.Column(db.String(100))


class Accountant(db.Model):
    __tablename__ = 'accountants'

    accountant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    designation = db.Column(db.String(100))


class Student(db.Model):
    __tablename__ = 'students'

    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    roll_no = db.Column(db.String(20), unique=True, nullable=False)
    course = db.Column(db.String(100))
    batch = db.Column(db.String(20))

    # Relationships
    user = db.relationship('User', back_populates='student_profile', foreign_keys=[user_id])
    allocations = db.relationship('RoomAllocation', back_populates='student', cascade='all, delete-orphan')
    complaints = db.relationship('Complaint', backref='student', cascade='all, delete-orphan')
    leave_requests = db.relationship('LeaveRequest', backref='student', cascade='all, delete-orphan')
    fees = db.relationship('Fee', backref='student', cascade='all, delete-orphan')
    visitors = db.relationship('Visitor', backref='student', cascade='all, delete-orphan')


class HostelBlock(db.Model):
    __tablename__ = 'hostel_blocks'

    block_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(200))

    rooms = db.relationship('Room', backref='block', cascade='all, delete-orphan')


class Room(db.Model):
    __tablename__ = 'rooms'
    __table_args__ = (
        db.UniqueConstraint('block_id', 'room_number', name='uq_block_room_number'),
        db.CheckConstraint('capacity > 0', name='ck_room_capacity_positive'),
        db.CheckConstraint('occupied_beds >= 0', name='ck_room_occupied_non_negative'),
        db.CheckConstraint('occupied_beds <= capacity', name='ck_room_occupied_within_capacity'),
        db.CheckConstraint("status IN ('available', 'full', 'maintenance')", name='ck_room_status_valid'),
    )

    room_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_number = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=2)
    occupied_beds = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='available')  # 'available', 'full', 'maintenance'
    block_id = db.Column(db.Integer, db.ForeignKey('hostel_blocks.block_id'), nullable=False)

    # Relationships
    allocations = db.relationship('RoomAllocation', back_populates='room', cascade='all, delete-orphan')

    def check_availability(self):
        return self.occupied_beds < self.capacity and self.status == 'available'

    def allocate_student(self):
        """Take one bed atomically.

        A single conditional UPDATE both checks availability and increments the
        counter, so two concurrent requests can never take the last bed. The
        in-memory object is refreshed afterwards. Returns True only if a bed
        was actually taken.
        """
        if self.room_id is None:
            return False
        stmt = (update(Room)
                .where(Room.room_id == self.room_id,
                       Room.occupied_beds < Room.capacity,
                       Room.status == 'available')
                .values(occupied_beds=Room.occupied_beds + 1,
                        status=case((Room.occupied_beds + 1 >= Room.capacity, 'full'),
                                    else_=Room.status))
                .execution_options(synchronize_session=False))
        if db.session.execute(stmt).rowcount != 1:
            return False
        db.session.refresh(self)
        return True

    def vacate_student(self):
        """Release one bed atomically (never below zero)."""
        if self.room_id is None:
            return False
        stmt = (update(Room)
                .where(Room.room_id == self.room_id, Room.occupied_beds > 0)
                .values(occupied_beds=Room.occupied_beds - 1,
                        status=case((Room.status == 'full', 'available'), else_=Room.status))
                .execution_options(synchronize_session=False))
        if db.session.execute(stmt).rowcount != 1:
            return False
        db.session.refresh(self)
        return True

    def __repr__(self):
        return f'<Room {self.room_number} (Floor {self.floor})>'


class RoomAllocation(db.Model):
    __tablename__ = 'room_allocations'
    # One *active* allocation per student is enforced by the database itself with a
    # partial unique index (supported by SQLite and PostgreSQL). MySQL has no partial
    # indexes, so there the application-level check in allocate() is the only guard.
    __table_args__ = (
        db.Index('uq_active_allocation_per_student', 'student_id', unique=True,
                 sqlite_where=text("status = 'active'"),
                 postgresql_where=text("status = 'active'")),
        db.CheckConstraint("status IN ('active', 'cancelled', 'completed')", name='ck_allocation_status_valid'),
    )

    allocation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.room_id'), nullable=False)
    allocation_date = db.Column(db.Date, nullable=False, default=date.today)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'cancelled', 'completed'

    room = db.relationship('Room', back_populates='allocations')
    student = db.relationship('Student', back_populates='allocations')

    @classmethod
    def has_active_allocation(cls, student_id):
        """Check if student already has an active allocation."""
        return cls.query.filter_by(student_id=student_id, status='active').first() is not None

    def allocate(self):
        # Check for existing active allocation (application-level enforcement for SQLite)
        if RoomAllocation.has_active_allocation(self.student_id):
            return False
        
        room = db.session.get(Room, self.room_id)
        if room and room.allocate_student():
            self.status = 'active'
            return True
        return False

    def reallocate(self, new_room_id):
        # Only allow reallocation of active allocations
        if self.status != 'active':
            return False
        
        new_room = db.session.get(Room, new_room_id)
        old_room = db.session.get(Room, self.room_id)
        if not new_room or not old_room:
            return False

        # Take the new bed first (atomic); only then release the old one, so a
        # failure never leaves the student without a bed or a counter out of step.
        if not new_room.allocate_student():
            return False
        old_room.vacate_student()
        self.room_id = new_room_id
        return True

    def cancel(self):
        # Only cancel active allocations, don't double-decrement
        if self.status != 'active':
            return False
        
        room = db.session.get(Room, self.room_id)
        if not room:
            # Room doesn't exist - inconsistent state
            return False

        room.vacate_student()
        self.status = 'cancelled'
        self.end_date = date.today()
        return True

    def __repr__(self):
        return f'<RoomAllocation Student:{self.student_id} Room:{self.room_id}>'


class Complaint(db.Model):
    __tablename__ = 'complaints'

    complaint_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'in_progress', 'resolved'

    def submit(self):
        self.status = 'pending'

    def update_status(self, new_status):
        valid_statuses = ['pending', 'in_progress', 'resolved']
        if new_status in valid_statuses:
            self.status = new_status
            return True
        return False

    def resolve(self):
        self.status = 'resolved'


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    leave_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'approved', 'rejected'

    def submit(self):
        self.status = 'pending'

    def approve(self):
        self.status = 'approved'

    def reject(self):
        self.status = 'rejected'


class Fee(db.Model):
    __tablename__ = 'fees'

    fee_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='unpaid')  # 'unpaid', 'paid', 'partial'
    paid_date = db.Column(db.Date, nullable=True)

    def record_payment(self, amount_paid):
        if amount_paid >= self.amount:
            self.status = 'paid'
            self.paid_date = date.today()
        elif amount_paid > 0:
            self.status = 'partial'
        return True

    def generate_receipt(self):
        return f"Receipt for Fee #{self.fee_id} - Student #{self.student_id}"

    def check_due(self):
        return self.status in ['unpaid', 'partial'] and self.due_date < date.today()


class Notice(db.Model):
    __tablename__ = 'notices'

    notice_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    publish_date = db.Column(db.Date, nullable=False, default=date.today)
    author_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    @staticmethod
    def publish(title, content, author_id):
        notice = Notice(title=title, content=content, author_id=author_id)
        db.session.add(notice)
        return notice

    @staticmethod
    def list_all():
        return Notice.query.order_by(Notice.publish_date.desc()).all()


class Visitor(db.Model):
    __tablename__ = 'visitors'

    visitor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    entry_time = db.Column(db.DateTime, nullable=False, default=_utcnow)
    exit_time = db.Column(db.DateTime, nullable=True)

    def log_entry(self):
        self.entry_time = _utcnow()

    def log_exit(self):
        self.exit_time = _utcnow()