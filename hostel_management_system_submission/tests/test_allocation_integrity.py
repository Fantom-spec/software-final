"""Capacity / state-consistency guarantees (counters, DB constraints, date range, filters)."""
from datetime import date, timedelta
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from hms_app.models import db, Room, RoomAllocation, HostelBlock, Student
from tests.helpers import soup


def _alloc(student, room, status='active'):
    return RoomAllocation(student_id=student.student_id, room_id=room.room_id, start_date=date.today(), status=status)


class TestAtomicCounters:
    def test_allocate_until_full_then_refuse(self, db_session, available_room):
        assert available_room.allocate_student() is True
        assert available_room.status == 'available' and available_room.occupied_beds == 1
        assert available_room.allocate_student() is True
        assert available_room.status == 'full' and available_room.occupied_beds == 2
        assert available_room.allocate_student() is False
        assert available_room.occupied_beds == 2

    def test_stale_object_cannot_oversubscribe(self, db_session, available_room):
        """Lost-update regression: another request fills the room after this one loaded it.

        The old read-modify-write code believed occupied_beds == 1 and allocated a third
        bed. The conditional UPDATE re-checks the *database* and refuses."""
        rid = available_room.room_id
        db_session.execute(text("UPDATE rooms SET occupied_beds = 1 WHERE room_id = :i"), {'i': rid})
        db_session.commit()
        room = db.session.get(Room, rid)
        assert room.occupied_beds == 1
        db_session.execute(text("UPDATE rooms SET occupied_beds = 2, status = 'full' WHERE room_id = :i"), {'i': rid})  # concurrent writer
        assert room.occupied_beds == 1  # still stale in memory
        assert room.allocate_student() is False
        assert db_session.execute(text("SELECT occupied_beds FROM rooms WHERE room_id = :i"), {'i': rid}).scalar() == 2

    def test_maintenance_room_refuses_allocation(self, db_session, maintenance_room):
        assert maintenance_room.allocate_student() is False
        assert maintenance_room.occupied_beds == 0

    def test_vacate_never_goes_below_zero(self, db_session, available_room):
        assert available_room.vacate_student() is False
        assert available_room.occupied_beds == 0

    def test_vacate_reopens_full_room(self, db_session, full_room):
        assert full_room.vacate_student() is True
        assert (full_room.occupied_beds, full_room.status) == (1, 'available')

    def test_maintenance_status_survives_vacate(self, db_session, maintenance_room):
        db_session.execute(text("UPDATE rooms SET occupied_beds = 1 WHERE room_id = :i"), {'i': maintenance_room.room_id})
        db_session.commit()
        db_session.refresh(maintenance_room)
        maintenance_room.vacate_student()
        assert maintenance_room.status == 'maintenance'


class TestDatabaseConstraints:
    def test_occupied_cannot_exceed_capacity(self, db_session, hostel_block):
        db_session.add(Room(block_id=hostel_block.block_id, room_number='X1', floor=1, capacity=2, occupied_beds=3))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_capacity_must_be_positive(self, db_session, hostel_block):
        db_session.add(Room(block_id=hostel_block.block_id, room_number='X2', floor=1, capacity=0))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_invalid_room_status_rejected(self, db_session, hostel_block):
        db_session.add(Room(block_id=hostel_block.block_id, room_number='X3', floor=1, capacity=2, status='haunted'))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_two_active_allocations_for_one_student_rejected(self, db_session, student_user, available_room, hostel_block):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        other = Room(block_id=hostel_block.block_id, room_number='Y1', floor=1, capacity=2)
        db_session.add(other)
        db_session.flush()
        db_session.add(_alloc(student, available_room))
        db_session.flush()
        db_session.add(_alloc(student, other))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_cancelled_history_plus_one_active_is_allowed(self, db_session, student_user, available_room, hostel_block):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        other = Room(block_id=hostel_block.block_id, room_number='Y2', floor=1, capacity=2)
        db_session.add(other)
        db_session.flush()
        db_session.add_all([_alloc(student, available_room, 'cancelled'), _alloc(student, other, 'cancelled'), _alloc(student, available_room, 'active')])
        db_session.flush()  # no error


class TestAllocationLifecycleConsistency:
    def _active(self, db_session, student, room):
        a = _alloc(student, room)
        assert a.allocate() is True
        db_session.add(a)
        db_session.commit()
        return a

    def test_reallocate_moves_exactly_one_bed(self, db_session, student_user, available_room, hostel_block):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        target = Room(block_id=hostel_block.block_id, room_number='T1', floor=1, capacity=2)
        db_session.add(target)
        db_session.commit()
        a = self._active(db_session, student, available_room)
        assert a.reallocate(target.room_id) is True
        db_session.commit()
        db_session.refresh(available_room)
        db_session.refresh(target)
        assert (available_room.occupied_beds, target.occupied_beds) == (0, 1)
        assert a.room_id == target.room_id

    def test_reallocate_to_full_room_changes_nothing(self, db_session, student_user, available_room, full_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        a = self._active(db_session, student, available_room)
        assert a.reallocate(full_room.room_id) is False
        db_session.commit()
        db_session.refresh(available_room)
        db_session.refresh(full_room)
        assert (available_room.occupied_beds, full_room.occupied_beds, a.room_id) == (1, 2, available_room.room_id)

    def test_cancel_frees_bed_and_reopens_room(self, db_session, student_user, hostel_block):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        room = Room(block_id=hostel_block.block_id, room_number='C1', floor=1, capacity=1)
        db_session.add(room)
        db_session.commit()
        a = self._active(db_session, student, room)
        assert db.session.get(Room, room.room_id).status == 'full'
        assert a.cancel() is True
        db_session.commit()
        room = db.session.get(Room, room.room_id)
        assert (room.occupied_beds, room.status, a.status) == (0, 'available', 'cancelled')


class TestRoutesBehavior:
    def _post(self, client, student, room, **kw):
        d = dict(student_id=student.student_id, room_id=room.room_id, start_date=date.today().isoformat())
        d.update(kw)
        return client.post('/allocation/create', data=d)

    @pytest.mark.parametrize('start,end', [('9999-12-31', ''), ('1900-01-01', ''), (date.today().isoformat(), '2200-01-01')])
    def test_out_of_range_dates_rejected(self, logged_in_admin, student_user, available_room, start, end):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        r = self._post(logged_in_admin, student, available_room, start_date=start, end_date=end)
        assert r.status_code == 200 and b'Dates must be between' in r.data
        assert RoomAllocation.query.count() == 0

    def test_malformed_date_rejected(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        r = self._post(logged_in_admin, student, available_room, start_date='2026-13-45')
        assert b'Invalid date format' in r.data and RoomAllocation.query.count() == 0

    def test_validation_error_keeps_user_input(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        r = self._post(logged_in_admin, student, available_room, end_date=yesterday)
        assert r.status_code == 200
        s = soup(r)
        assert s.select_one('#student_id option[selected]')['value'] == str(student.student_id)
        assert s.select_one('#room_id option[selected]')['value'] == str(available_room.room_id)
        assert s.select_one('#start_date')['value'] == date.today().isoformat()
        assert s.select_one('#end_date')['value'] == yesterday
        assert 'cannot be earlier' in s.get_text()
        assert RoomAllocation.query.count() == 0

    def test_show_all_respects_block_filter(self, logged_in_admin, db_session, hostel_block, full_room):
        zeta = HostelBlock(name='Zeta Block', location='Z')
        db_session.add(zeta)
        db_session.flush()
        db_session.add(Room(block_id=zeta.block_id, room_number='900', floor=1, capacity=2))
        db_session.commit()

        def listing(block):
            s = soup(logged_in_admin.get(f'/allocation/available?show_all=true&block={block.block_id}'))
            for sel in s.find_all('select'):
                sel.decompose()
            return s.find('main').get_text(' ', strip=True)

        assert hostel_block.name not in listing(zeta)       # full room of 'Test Block' must not leak into Zeta's view
        assert hostel_block.name in listing(hostel_block)   # but is shown for its own block

    def test_cancel_via_get_not_allowed(self, logged_in_admin, student_user, available_room):
        student = Student.query.filter_by(user_id=student_user.user_id).first()
        a = _alloc(student, available_room)
        a.allocate()
        db.session.add(a)
        db.session.commit()
        assert logged_in_admin.get(f'/allocation/{a.allocation_id}/cancel').status_code == 405
        assert db.session.get(RoomAllocation, a.allocation_id).status == 'active'
