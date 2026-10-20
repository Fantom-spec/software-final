from flask import Blueprint, render_template, redirect, url_for, flash, request
from hms_app.auth import login_required, role_required, get_current_user
from hms_app.models import db, User, Student, Room, RoomAllocation, HostelBlock
from datetime import date
from sqlalchemy.exc import IntegrityError


room_alloc_bp = Blueprint('room_allocation', __name__, url_prefix='/allocation')


@room_alloc_bp.route('/')
@login_required
@role_required('admin', 'warden')
def index():
    allocations = (RoomAllocation.query
        .filter_by(status='active')
        .join(Student, RoomAllocation.student_id == Student.student_id)
        .join(User, Student.user_id == User.user_id)
        .join(Room, RoomAllocation.room_id == Room.room_id)
        .join(HostelBlock, Room.block_id == HostelBlock.block_id)
        .order_by(User.name)
        .all())
    return render_template('allocation/index.html', allocations=allocations)


@room_alloc_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warden')
def create():
    if request.method == 'POST':
        student_id = request.form.get('student_id', type=int)
        room_id = request.form.get('room_id', type=int)
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Validation
        if not student_id or not room_id or not start_date_str:
            flash('Student, room, and start date are required.', 'error')
            return redirect(url_for('room_allocation.create'))
        
        student = Student.query.get(student_id)
        room = Room.query.get(room_id)
        
        if not student:
            flash('Selected student does not exist.', 'error')
            return redirect(url_for('room_allocation.create'))
        
        if not room:
            flash('Selected room does not exist.', 'error')
            return redirect(url_for('room_allocation.create'))
        
        # Check if student already has an active allocation (using model method)
        if RoomAllocation.has_active_allocation(student_id):
            flash(f'Student {student.user.name} already has an active room allocation.', 'error')
            return redirect(url_for('room_allocation.create'))
        
        # Check room availability
        if not room.check_availability():
            flash(f'Room {room.room_number} is not available (capacity: {room.capacity}, occupied: {room.occupied_beds}).', 'error')
            return redirect(url_for('room_allocation.create'))
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str) if end_date_str else None
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'error')
            return redirect(url_for('room_allocation.create'))
        
        # Validate date range
        if end_date and end_date < start_date:
            flash('End date cannot be earlier than start date.', 'error')
            return redirect(url_for('room_allocation.create'))
        
        # Create allocation
        allocation = RoomAllocation(
            student_id=student_id,
            room_id=room_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Use transaction with retry logic for concurrency
        # NOTE: SQLite does not support SELECT FOR UPDATE or row-level locking.
        # This implementation uses a check-then-act pattern with application-level
        # duplicate detection (RoomAllocation.has_active_allocation) and retry logic
        # for IntegrityError. However, this does NOT provide true concurrency safety:
        # - Between check_availability() and room.allocate_student(), another request
        #   could allocate the last bed (time-of-check/time-of-use race).
        # - RoomAllocation.has_active_allocation() and allocate() are not atomic.
        # For production MySQL/PostgreSQL deployment, replace with:
        #   room = Room.query.with_for_update().get(room_id)  -- row-level lock
        #   allocation = RoomAllocation(...) with DB-level partial unique index
        #   Single transaction with SERIALIZABLE isolation level
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if allocation.allocate():
                    db.session.add(allocation)
                    db.session.commit()
                    flash(f'Room {room.room_number} allocated to {student.user.name} successfully.', 'success')
                    return redirect(url_for('room_allocation.index'))
                else:
                    flash('Allocation failed. Student may already have an allocation or room is unavailable.', 'error')
                    return redirect(url_for('room_allocation.create'))
            except IntegrityError:
                db.session.rollback()
                if attempt == max_retries - 1:
                    flash('Allocation failed due to concurrent modification. Please try again.', 'error')
                    return redirect(url_for('room_allocation.create'))
                # Retry on next iteration
        
        return redirect(url_for('room_allocation.create'))
    
    # GET request - show form
    students = Student.query.join(User).order_by(User.name).all()
    available_rooms = (Room.query.filter(Room.occupied_beds < Room.capacity, Room.status == 'available')
                       .join(HostelBlock).order_by(HostelBlock.name, Room.floor, Room.room_number).all())
    return render_template('allocation/create.html', students=students, rooms=available_rooms, today=date.today().isoformat())


@room_alloc_bp.route('/<int:allocation_id>/reallocate', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'warden')
def reallocate(allocation_id):
    allocation = RoomAllocation.query.get_or_404(allocation_id)

    if allocation.status != 'active':
        flash('Only active allocations can be reallocated.', 'error')
        return redirect(url_for('room_allocation.index'))
    
    if request.method == 'POST':
        new_room_id = request.form.get('new_room_id', type=int)
        
        if not new_room_id:
            flash('New room is required.', 'error')
            return redirect(url_for('room_allocation.reallocate', allocation_id=allocation_id))
        
        new_room = Room.query.get(new_room_id)
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
    allocation = RoomAllocation.query.get_or_404(allocation_id)
    
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
    rooms = (Room.query.filter(Room.occupied_beds < Room.capacity, Room.status == 'available')
             .join(HostelBlock).order_by(HostelBlock.name, Room.floor, Room.room_number).all())
    return render_template('allocation/available.html', rooms=rooms)


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

    student = Student.query.get_or_404(student_id)
    allocation = RoomAllocation.query.filter_by(student_id=student_id, status='active').first()
    return render_template('allocation/student_view.html', allocation=allocation, student=student)