"""Admin-only data entry: hostel blocks, rooms and students.

All three forms are server-validated (the browser checks are only a convenience),
CSRF-protected by the application-wide CSRFProtect, and re-render with the user's
input on error.
"""
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from sqlalchemy.exc import IntegrityError
from hms_app.auth import login_required, role_required
from hms_app.models import db, User, Student, Room, HostelBlock

admin_data_bp = Blueprint('admin_data', __name__)

MAX_FLOOR = 50
MAX_CAPACITY = 10
MIN_PASSWORD = 8
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
ROLL_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]*$')


def _clean(name):
    return (request.form.get(name) or '').strip()


# ----------------------------------------------------------------- blocks
@admin_data_bp.route('/blocks/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def new_block():
    if request.method == 'GET':
        return render_template('admin/block_form.html', form={})

    name, location = _clean('name'), _clean('location')

    def fail(msg):
        flash(msg, 'error')
        return render_template('admin/block_form.html', form=request.form)

    if not name:
        return fail('Block name is required.')
    if len(name) > 50:
        return fail('Block name must be at most 50 characters.')
    if len(location) > 200:
        return fail('Location must be at most 200 characters.')
    if HostelBlock.query.filter(db.func.lower(HostelBlock.name) == name.lower()).first():
        return fail(f'A block named "{name}" already exists.')

    db.session.add(HostelBlock(name=name, location=location or None))
    db.session.commit()
    flash(f'Block "{name}" added.', 'success')
    return redirect(url_for('main.rooms_list'))


# ----------------------------------------------------------------- rooms
@admin_data_bp.route('/rooms/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def new_room():
    blocks = HostelBlock.query.order_by(HostelBlock.name).all()

    def render(form, status=200):
        return render_template('admin/room_form.html', form=form, blocks=blocks, max_floor=MAX_FLOOR, max_capacity=MAX_CAPACITY), status

    if request.method == 'GET':
        return render({})

    def fail(msg):
        flash(msg, 'error')
        return render(request.form)

    block_id = request.form.get('block_id', type=int)
    number = _clean('room_number')
    floor = request.form.get('floor', type=int)
    capacity = request.form.get('capacity', type=int)
    status = _clean('status') or 'available'

    block = db.session.get(HostelBlock, block_id) if block_id else None
    if not block:
        return fail('Please choose an existing block.')
    if not number:
        return fail('Room number is required.')
    if len(number) > 20:
        return fail('Room number must be at most 20 characters.')
    if floor is None or not (0 <= floor <= MAX_FLOOR):
        return fail(f'Floor must be a whole number from 0 to {MAX_FLOOR}.')
    if capacity is None or not (1 <= capacity <= MAX_CAPACITY):
        return fail(f'Capacity must be a whole number from 1 to {MAX_CAPACITY}.')
    if status not in ('available', 'maintenance'):
        return fail('Status must be Available or Maintenance.')
    if Room.query.filter(Room.block_id == block.block_id, db.func.lower(Room.room_number) == number.lower()).first():
        return fail(f'Room {number} already exists in {block.name}.')

    try:
        db.session.add(Room(block_id=block.block_id, room_number=number, floor=floor, capacity=capacity, status=status))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail(f'Room {number} could not be added (it may already exist in {block.name}).')
    flash(f'Room {number} added to {block.name}.', 'success')
    return redirect(url_for('main.rooms_list'))


# ----------------------------------------------------------------- students
@admin_data_bp.route('/students/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def new_student():
    if request.method == 'GET':
        return render_template('admin/student_form.html', form={}, min_password=MIN_PASSWORD)

    name, email = _clean('name'), _clean('email').lower()
    roll_no, course, batch = _clean('roll_no'), _clean('course'), _clean('batch')
    password, confirm = request.form.get('password', ''), request.form.get('confirm_password', '')

    def fail(msg):
        flash(msg, 'error')
        # never echo passwords back into the page
        kept = {k: v for k, v in request.form.items() if k not in ('password', 'confirm_password')}
        return render_template('admin/student_form.html', form=kept, min_password=MIN_PASSWORD)

    if not name:
        return fail('Name is required.')
    if len(name) > 100:
        return fail('Name must be at most 100 characters.')
    if not email or len(email) > 120 or not EMAIL_RE.match(email):
        return fail('Enter a valid e-mail address (at most 120 characters).')
    if not roll_no or len(roll_no) > 20 or not ROLL_RE.match(roll_no):
        return fail('Roll number is required (letters, digits, . _ / - ; at most 20 characters).')
    if len(course) > 100:
        return fail('Course must be at most 100 characters.')
    if len(batch) > 20:
        return fail('Batch must be at most 20 characters.')
    if len(password) < MIN_PASSWORD or len(password) > 128:
        return fail(f'Password must be {MIN_PASSWORD} to 128 characters long.')
    if password != confirm:
        return fail('The two passwords do not match.')
    if User.query.filter(db.func.lower(User.email) == email).first():
        return fail(f'A user with e-mail {email} already exists.')
    if Student.query.filter(db.func.lower(Student.roll_no) == roll_no.lower()).first():
        return fail(f'Roll number {roll_no} is already in use.')

    try:
        user = User(name=name, email=email, role='student')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(Student(user_id=user.user_id, roll_no=roll_no, course=course or None, batch=batch or None))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail('The student could not be added (e-mail or roll number already in use).')
    flash(f'Student {name} ({roll_no}) added.', 'success')
    return redirect(url_for('main.students_list'))
