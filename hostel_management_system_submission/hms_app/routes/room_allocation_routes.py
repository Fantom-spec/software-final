from flask import Blueprint, current_app, render_template, redirect, url_for, flash, request
from hms_app.auth import login_required, role_required, get_current_user
from hms_app.models import db, User, Student, Room, RoomAllocation, HostelBlock
from datetime import date
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_


room_alloc_bp = Blueprint('room_allocation', __name__, url_prefix='/allocation')


@room_alloc_bp.route('/')
@login_required
@role_required('admin', 'warden')
def index():
    # Get search and filter parameters
    search = request.args.get('search', '').strip()
    block_filter = request.args.get('block', '')
    status_filter = request.args.get('status', 'active')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = (RoomAllocation.query
             .join(Student, RoomAllocation.student_id == Student.student_id)
             .join(User, Student.user_id == User.user_id)
             .join(Room, RoomAllocation.room_id == Room.room_id)
             .join(HostelBlock, Room.block_id == HostelBlock.block_id))

    # Apply status filter
    if status_filter:
        query = query.filter(RoomAllocation.status == status_filter)

    # Apply block filter
    if block_filter:
        query = query.filter(HostelBlock.block_id == block_filter)

    # Apply search
    if search:
        query = query.filter(or_(
            User.name.ilike(f'%{search}%'),
            Student.roll_no.ilike(f'%{search}%'),
            Room.room_number.ilike(f'%{search}%'),
            HostelBlock.name.ilike(f'%{search}%')
        ))

    query = query.order_by(User.name)

    # Get total count for pagination info
    total = query.count()

    # Apply pagination
    allocations = query.offset((page - 1) * per_page).limit(per_page).all()

    # Get blocks for filter dropdown
    blocks = HostelBlock.query.order_by(HostelBlock.name).all()

    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    # Calculate page range for pagination display
    start_page = max(1, page - 2)
    end_page = min(total_pages + 1, page + 3)
    page_range = range(start_page, end_page)

    return render_template('allocation/index.html',
                           allocations=allocations,
                           blocks=blocks,
                           search=search,
                           block_filter=block_filter,
                           status_filter=status_filter,
                           page=page,
                           total_pages=total_pages,
                           has_prev=has_prev,
                           has_next=has_next,
                           total=total,
                           per_page=per_page,
                           page_range=page_range)


def _parse_allocation_dates(start_str, end_str):
    """Return (start, end, error_message). Dates must be ISO and inside the sanity range."""
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str) if end_str else None
    except ValueError:
        return None, None, 'Invalid date format. Use YYYY-MM-DD.'
    lo = date.fromisoformat(current_app.config['MIN_ALLOCATION_DATE'])
    hi = date.fromisoformat(current_app.config['MAX_ALLOCATION_DATE'])
    for value in (start, end):
        if value is not None and not (lo <= value <= hi):
            return None, None, f'Dates must be between {lo.isoformat()} and {hi.isoformat()}.'
    if end and end < start:
        return None, None, 'End date cannot be earlier than start date.'
    return start, end, None


def _render_create_form(form=None, status=200):
    students = Student.query.join(User).order_by(User.name).all()
    available_rooms = (Room.query.filter(Room.occupied_beds < Room.capacity, Room.status == 'available')
                       .join(HostelBlock).order_by(HostelBlock.name, Room.floor, Room.room_number).all())
    return render_template('allocation/create.html', students=students, rooms=available_rooms,
                           today=date.today().isoformat(), form=form or {}), status


@room_alloc_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warden')
def create():
    if request.method == 'GET':
        return _render_create_form()

    student_id = request.form.get('student_id', type=int)
    room_id = request.form.get('room_id', type=int)
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    def fail(message):
        # Re-render (not redirect) so the user's selections are kept.
        flash(message, 'error')
        return _render_create_form(request.form)

    if not student_id or not room_id or not start_date_str:
        return fail('Student, room, and start date are required.')

    student = db.session.get(Student, student_id)
    room = db.session.get(Room, room_id)
    if not student:
        return fail('Selected student does not exist.')
    if not room:
        return fail('Selected room does not exist.')
    if RoomAllocation.has_active_allocation(student_id):
        return fail(f'Student {student.user.name} already has an active room allocation.')
    if not room.check_availability():
        return fail(f'Room {room.room_number} is not available (capacity: {room.capacity}, occupied: {room.occupied_beds}).')

    start_date, end_date, error = _parse_allocation_dates(start_date_str, end_date_str)
    if error:
        return fail(error)

    allocation = RoomAllocation(student_id=student_id, room_id=room_id,
                                start_date=start_date, end_date=end_date)
    try:
        # allocate() takes the bed with one atomic UPDATE; the partial unique index
        # on (student_id) WHERE status='active' backstops duplicate allocations.
        if not allocation.allocate():
            db.session.rollback()
            return fail('Allocation failed: the room has just become unavailable or the student already has an allocation.')
        db.session.add(allocation)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return fail('Allocation conflicted with another request. Please review the current state and try again.')

    flash(f'Room {room.room_number} allocated to {student.user.name} successfully.', 'success')
    return redirect(url_for('room_allocation.index'))


@room_alloc_bp.route('/<int:allocation_id>/reallocate', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warden')
def reallocate(allocation_id):
    allocation = db.get_or_404(RoomAllocation, allocation_id)

    if allocation.status != 'active':
        flash('Only active allocations can be reallocated.', 'error')
        return redirect(url_for('room_allocation.index'))

    if request.method == 'POST':
        new_room_id = request.form.get('new_room_id', type=int)

        if not new_room_id:
            flash('New room is required.', 'error')
            return redirect(url_for('room_allocation.reallocate', allocation_id=allocation_id))

        new_room = db.session.get(Room, new_room_id)
        if not new_room:
            flash('Selected room does not exist.', 'error')
            return redirect(url_for('room_allocation.reallocate', allocation_id=allocation_id))

        if new_room.room_id == allocation.room_id:
            flash('Student is already in that room. Choose a different room.', 'error')
            return redirect(url_for('room_allocation.reallocate', allocation_id=allocation_id))

        if not new_room.check_availability():
            flash(f'Room {new_room.room_number} is not available.', 'error')
            return redirect(url_for('room_allocation.reallocate', allocation_id=allocation_id))

        if allocation.reallocate(new_room_id):
            db.session.commit()
            flash(f'Student reallocated to room {new_room.room_number} successfully.', 'success')
            return redirect(url_for('room_allocation.index'))
        else:
            flash('Reallocation failed.', 'error')
            return redirect(url_for('room_allocation.reallocate', allocation_id=allocation_id))

    # GET request
    available_rooms = (Room.query.filter(Room.occupied_beds < Room.capacity, Room.status == 'available')
                       .join(HostelBlock).order_by(HostelBlock.name, Room.floor, Room.room_number).all())
    return render_template('allocation/reallocate.html', allocation=allocation, rooms=available_rooms)


@room_alloc_bp.route('/<int:allocation_id>/cancel', methods=['POST'])
@login_required
@role_required('admin', 'warden')
def cancel(allocation_id):
    allocation = db.get_or_404(RoomAllocation, allocation_id)

    if allocation.cancel():
        db.session.commit()
        flash('Allocation cancelled successfully.', 'success')
    else:
        flash('Cancellation failed.', 'error')

    return redirect(url_for('room_allocation.index'))


@room_alloc_bp.route('/available')
@login_required
@role_required('admin', 'warden', 'student')
def available_rooms():
    # Get filter parameters
    block_filter = request.args.get('block', '')
    show_all = request.args.get('show_all', 'false')

    query = Room.query.filter(Room.occupied_beds < Room.capacity, Room.status == 'available').join(HostelBlock)

    if block_filter:
        query = query.filter(HostelBlock.block_id == block_filter)

    rooms = query.order_by(HostelBlock.name, Room.floor, Room.room_number).all()

    # If show_all is true, also show full rooms
    if show_all == 'true':
        full_query = Room.query.filter(Room.status == 'full').join(HostelBlock)
        if block_filter:
            full_query = full_query.filter(HostelBlock.block_id == block_filter)
        full_rooms = full_query.order_by(HostelBlock.name, Room.floor, Room.room_number).all()
    else:
        full_rooms = []

    blocks = HostelBlock.query.order_by(HostelBlock.name).all()

    return render_template('allocation/available.html',
                           rooms=rooms,
                           full_rooms=full_rooms,
                           blocks=blocks,
                           block_filter=block_filter,
                           show_all=show_all)


@room_alloc_bp.route('/student/<int:student_id>')
@login_required
def student_allocation(student_id):
    user = get_current_user()
    # Students can only view their own allocation
    if user.is_student() and user.student_profile.student_id != student_id:
        flash('You can only view your own allocation.', 'error')
        return redirect(url_for('main.dashboard'))

    if user.is_student() and not user.student_profile:
        return redirect(url_for('main.dashboard'))
    if user.is_accountant():
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('main.dashboard'))

    student = db.get_or_404(Student, student_id)
    allocation = RoomAllocation.query.filter_by(student_id=student_id, status='active').first()
    return render_template('allocation/student_view.html', allocation=allocation, student=student)