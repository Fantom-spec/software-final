from flask import Blueprint, render_template, redirect, url_for, flash, request
from hms_app.auth import login_required, role_required, get_current_user
from hms_app.models import db, User, Student, Room, RoomAllocation, HostelBlock


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    if user.is_admin():
        stats = {
            'total_students': Student.query.count(),
            'total_rooms': Room.query.count(),
            'occupied_rooms': Room.query.filter(Room.occupied_beds > 0).count(),
            'available_rooms': Room.query.filter(Room.occupied_beds < Room.capacity, Room.status == 'available').count(),
            'active_allocations': RoomAllocation.query.filter_by(status='active').count(),
            'total_beds': db.session.query(db.func.coalesce(db.func.sum(Room.capacity), 0)).scalar(),
            'used_beds': db.session.query(db.func.coalesce(db.func.sum(Room.occupied_beds), 0)).scalar(),
        }
        recent = (RoomAllocation.query.order_by(RoomAllocation.allocation_id.desc()).limit(5).all())
        return render_template('dashboard_admin.html', stats=stats, recent=recent)
    
    elif user.is_warden():
        rooms = Room.query.join(HostelBlock).order_by(HostelBlock.name, Room.floor, Room.room_number).all()
        return render_template('dashboard_warden.html', rooms=rooms)
    
    elif user.is_student():
        student = user.student_profile
        if not student:
            flash('No student profile is linked to your account. Please contact the administrator.', 'warning')
            return render_template('dashboard_message.html', user=user)
        allocation = RoomAllocation.query.filter_by(student_id=student.student_id, status='active').first()
        return render_template('dashboard_student.html', student=student, allocation=allocation)
    
    elif user.is_accountant():
        return render_template('dashboard_accountant.html')
    
    flash('Your account role is not recognised.', 'error')
    return render_template('dashboard_message.html', user=user)


@main_bp.route('/rooms')
@login_required
@role_required('admin', 'warden')
def rooms_list():
    rooms = Room.query.join(HostelBlock).order_by(HostelBlock.name, Room.floor, Room.room_number).all()
    return render_template('rooms_list.html', rooms=rooms)


@main_bp.route('/students')
@login_required
@role_required('admin', 'warden')
def students_list():
    students = Student.query.join(User).order_by(User.name).all()
    return render_template('students_list.html', students=students)