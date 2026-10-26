"""Shared helpers for tests that need their own app instance (not the session-wide one)."""
import re
from datetime import date
from bs4 import BeautifulSoup
from hms_app import create_app
from hms_app.config import TestConfig
from hms_app.models import db, User, Student, Room, HostelBlock, RoomAllocation


def make_app(**overrides):
    """Fresh app + fresh in-memory database, with config overrides."""
    cfg = type('Cfg', (TestConfig,), overrides)
    return create_app(cfg)


def populate(app):
    """Admin, two students, a block with two rooms. Returns plain ids (no ORM objects)."""
    with app.app_context():
        admin = User(name='Admin', email='admin@t.test', role='admin'); admin.set_password('Admin#12345')
        s_users = []
        for i in (1, 2):
            u = User(name=f'Stud {i}', email=f's{i}@t.test', role='student'); u.set_password('Stud#12345')
            s_users.append(u)
        db.session.add_all([admin] + s_users)
        db.session.flush()
        studs = [Student(user_id=u.user_id, roll_no=f'R{i}', course='C', batch='2024') for i, u in enumerate(s_users, 1)]
        block = HostelBlock(name='Alpha', location='X')
        db.session.add_all(studs + [block])
        db.session.flush()
        r1 = Room(block_id=block.block_id, room_number='101', floor=1, capacity=2)
        r2 = Room(block_id=block.block_id, room_number='102', floor=1, capacity=2)
        db.session.add_all([r1, r2])
        db.session.commit()
        return dict(student_ids=[s.student_id for s in studs], room_ids=[r1.room_id, r2.room_id], block_id=block.block_id)


def token(client, url):
    """Read the CSRF token from a rendered form."""
    html = client.get(url).data
    el = BeautifulSoup(html, 'html.parser').find('input', {'name': 'csrf_token'})
    return el['value'] if el else None


def login(client, email, password, with_token=True):
    data = {'email': email, 'password': password}
    if with_token:
        data['csrf_token'] = token(client, '/auth/login')
    return client.post('/auth/login', data=data)


def soup(resp):
    return BeautifulSoup(resp.data, 'html.parser')


def count_allocations(app, **filters):
    with app.app_context():
        return RoomAllocation.query.filter_by(**filters).count()
