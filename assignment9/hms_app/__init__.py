from flask import Flask, render_template, redirect, url_for, flash, request, session
from hms_app.config import Config, TestConfig
from hms_app.models import db, User, Student, Room, RoomAllocation, HostelBlock, Warden, Admin, Accountant
from hms_app.auth import login_required, role_required, login_user, logout_user, get_current_user
from datetime import date, datetime
import os
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_wtf.csrf import CSRFProtect


csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_app(config_class=Config):
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    app.config.from_object(config_class)

    db.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from hms_app.routes.auth_routes import auth_bp
    from hms_app.routes.room_allocation_routes import room_alloc_bp
    from hms_app.routes.main_routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(room_alloc_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_user():
        return dict(current_user=get_current_user())

    @app.context_processor
    def inject_app_info():
        return dict(app_name=app.config.get('APP_NAME', 'Hostel Management System'),
                    app_short_name=app.config.get('APP_SHORT_NAME', 'HMS'))

    with app.app_context():
        db.create_all()
        init_sample_data()

    return app


def init_sample_data():
    """Initialize sample data for testing"""
    if User.query.first():
        return  # Data already exists

    # Create admin user
    admin_user = User(name='Admin User', email='admin@hms.test', role='admin')
    admin_user.set_password('admin123')
    db.session.add(admin_user)
    db.session.flush()
    admin = Admin(user_id=admin_user.user_id, designation='System Administrator')
    db.session.add(admin)

    # Create warden user
    warden_user = User(name='Warden Smith', email='warden@hms.test', role='warden')
    warden_user.set_password('warden123')
    db.session.add(warden_user)
    db.session.flush()
    warden = Warden(user_id=warden_user.user_id, department='Boys Hostel Block A')
    db.session.add(warden)

    # Create student users
    students_data = [
        ('John Doe', 'john@student.test', 'STU001', 'B.Tech CSE', '2023'),
        ('Jane Smith', 'jane@student.test', 'STU002', 'B.Tech ECE', '2023'),
        ('Bob Wilson', 'bob@student.test', 'STU003', 'B.Tech ME', '2022'),
    ]

    for name, email, roll_no, course, batch in students_data:
        user = User(name=name, email=email, role='student')
        user.set_password('student123')
        db.session.add(user)
        db.session.flush()
        student = Student(user_id=user.user_id, roll_no=roll_no, course=course, batch=batch)
        db.session.add(student)

    # Create accountant user
    acc_user = User(name='Accountant Brown', email='accountant@hms.test', role='accountant')
    acc_user.set_password('accountant123')
    db.session.add(acc_user)
    db.session.flush()
    acc = Accountant(user_id=acc_user.user_id, designation='Fee Accountant')
    db.session.add(acc)

    # Create hostel blocks and rooms
    block_a = HostelBlock(name='Block A', location='Main Campus')
    block_b = HostelBlock(name='Block B', location='East Campus')
    db.session.add_all([block_a, block_b])
    db.session.flush()

    # Block A rooms (2 rooms, capacity 2 each)
    rooms_data = [
        (block_a.block_id, '101', 1, 2),
        (block_a.block_id, '102', 1, 2),
        (block_a.block_id, '201', 2, 2),
        (block_a.block_id, '202', 2, 2),
        (block_b.block_id, '101', 1, 3),
        (block_b.block_id, '102', 1, 3),
    ]

    for block_id, room_num, floor, cap in rooms_data:
        room = Room(block_id=block_id, room_number=room_num, floor=floor, capacity=cap)
        db.session.add(room)

    db.session.commit()


# For running directly
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)