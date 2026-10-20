# HMS Test Application

Minimal Flask implementation of the Hostel Management System Room Allocation module for Assessment 8 testing.

## Structure

```
hms_app/
├── __init__.py          # App factory and initialization
├── config.py            # Configuration classes
├── models.py            # SQLAlchemy models
├── auth.py              # Authentication helpers
└── routes/
    ├── auth_routes.py   # Login/logout
    ├── main_routes.py   # Dashboards, room/student lists
    └── room_allocation_routes.py  # Room allocation CRUD
```

## Models (matching Class Diagram)

- **User** - Base user with role-based access (admin, warden, student, accountant)
- **Student** - Student profile with roll_no, course, batch
- **Room** - Room with capacity, occupied_beds, status
- **RoomAllocation** - Links students to rooms with dates and status
- **HostelBlock** - Hostel blocks containing rooms
- **Warden, Admin, Accountant** - Role-specific extensions

## Running the Application

```bash
cd assignment8
pip install -r requirements-test.txt
python -m hms_app
```

Access at http://localhost:5000

## Test Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@hms.test | admin123 |
| Warden | warden@hms.test | warden123 |
| Student | john@student.test | student123 |
| Accountant | accountant@hms.test | accountant123 |

## Room Allocation Workflow

1. Admin/Warden logs in
2. Navigate to "New Allocation" or `/allocation/create`
3. Select student and available room
4. Set start date (and optional end date)
5. Submit - system validates availability and prevents duplicates
6. View all allocations at `/allocation/`
7. Reallocate or cancel as needed

## Testing

Run automated tests:
```bash
cd assignment8
python -m pytest tests/ -v
```

Run with coverage:
```bash
python -m pytest tests/ --cov=hms_app --cov-report=html
```