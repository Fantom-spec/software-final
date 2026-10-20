# Assessment 9 — Hostel Management System UI Design and Development

**Course:** BCSE301P — Software Engineering  
**Module:** Room Allocation (UI)  
**Date:** 2026-10-20  
**Version:** 1.0

---

## Overview

This project implements **Assessment 9: Design and Development of a User Interface for the Hostel Management System**, building upon the Assignment 8 backend implementation. It provides a polished, responsive, accessible Bootstrap 5 interface for managing room allocations with full integration to the existing Flask application, SQLAlchemy models, and role-based authorization system.

---

## Features Implemented

### Core UI Module: Room Allocation
- **Allocations List** — Searchable, filterable, paginated table with reallocate/cancel actions
- **Create Allocation** — Student/room selection with real-time availability preview, date validation
- **Reallocate Room** — Side-by-side current vs new room comparison with availability check
- **Cancel Allocation** — Confirmation prompt, proper state cleanup
- **Available Rooms** — Filterable list with occupancy visualization, optional full rooms view
- **Student Personal View** — Restricted to own allocation with room details

### Role-Based Dashboards
- **Admin Dashboard** — Summary stats (students, rooms, beds, allocations), occupancy progress bar, quick actions, recent allocations
- **Warden Dashboard** — Room status table with occupancy bars, availability summary cards
- **Student Dashboard** — Profile card + allocation card (or "no allocation" state with link to available rooms)
- **Accountant Dashboard** — Placeholder for future fee management

### Supporting Pages
- **Room Management** — Searchable table with occupancy/status
- **Student Management** — Searchable table with allocation badge
- **Login** — Demo account quick-fill, password toggle, CSRF protected

### Technical Features
- **Responsive Sidebar Layout** — Collapsible on mobile (<992px), overlay backdrop
- **Breadcrumb Navigation** — Context-aware on all pages
- **Flash Messages** — Success/error/warning/info with auto-dismiss (5s), icons
- **Form Validation** — HTML5 + server-side, inline messages, loading states
- **Real-time Availability Preview** — Updates instantly when room selected
- **Dark Mode** — Automatic via `prefers-color-scheme`
- **Print Styles** — Content-only output
- **Accessibility** — Semantic HTML, ARIA labels, focus indicators, keyboard navigation
- **CSRF Protection** — All state-changing forms

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.0.3, Python 3.11+ |
| Database | SQLite (dev/test), MySQL 8.x (production spec) |
| ORM | SQLAlchemy 2.0, Flask-SQLAlchemy 3.1 |
| Auth | Flask-Login 0.6, bcrypt 4.2 |
| CSRF | Flask-WTF CSRFProtect |
| Frontend | Bootstrap 5.3.3, Bootstrap Icons 1.11.3, vanilla JS |
| Templates | Jinja2 with macro-based components |
| Testing | pytest 8.3, pytest-cov 5.0, pytest-flask 1.3 |

---

## Folder Structure

```
assignment9/
├── README.md                      # This file
├── requirements.txt               # Application dependencies
├── requirements-test.txt          # Test dependencies
├── run.py                         # Application entry point
├── scripts/
│   └── run_tests.py              # Test runner with coverage
├── hms_app/
│   ├── __init__.py               # App factory, CSRF, sample data
│   ├── config.py                 # Config classes (Config, TestConfig)
│   ├── models.py                 # SQLAlchemy models (from Assignment 8)
│   ├── auth.py                   # Auth helpers (from Assignment 8)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py        # Login/logout
│   │   ├── main_routes.py        # Dashboards, rooms, students
│   │   └── room_allocation_routes.py  # Allocation CRUD + search/filter
│   ├── static/
│   │   └── css/
│   │       └── hms.css           # Complete design system
│   └── templates/
│       ├── base.html             # Shared layout with sidebar
│       ├── login.html
│       ├── _macros.html          # Reusable template macros
│       ├── dashboard_admin.html
│       ├── dashboard_warden.html
│       ├── dashboard_student.html
│       ├── dashboard_accountant.html
│       ├── dashboard_message.html
│       ├── rooms_list.html
│       ├── students_list.html
│       └── allocation/
│           ├── index.html        # Allocations list with search/filter/pagination
│           ├── create.html       # Create allocation form
│           ├── reallocate.html   # Reallocate form
│           ├── available.html    # Available rooms
│           └── student_view.html # Student personal allocation
├── tests/
│   ├── conftest.py               # Pytest fixtures
│   ├── test_room_allocation.py   # 42 allocation workflow tests
│   ├── test_validation.py        # 18 validation/constraint tests
│   ├── test_authorization.py     - 32 auth/authorization tests
│   └── test_ui.py                # 26 UI rendering/accessibility tests
├── docs/
│   ├── ui_design.md              # UI design rationale and specifications
│   └── requirement_traceability.md  # Requirement traceability matrix
├── screenshots/                  # (Capture from running app)
└── instance/                     # SQLite database (created at runtime)
```

---

## Installation

### Prerequisites
- Python 3.11+
- pip

### Setup
```bash
cd assignment9
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

---

## Running the Application

```bash
# Development server
python run.py
# or
python -m hms_app
```

The application will be available at **http://localhost:5000**

### Demo Accounts (if `SHOW_DEMO_CREDENTIALS=1`)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@hms.test | admin123 |
| Warden | warden@hms.test | warden123 |
| Student | john@student.test | student123 |
| Accountant | accountant@hms.test | accountant123 |

---

## Running Tests

```bash
# Full test suite with coverage
python -m pytest tests/ -v --cov=hms_app --cov-report=term-missing --cov-report=html:results/coverage_html

# Or use the runner script
python scripts/run_tests.py

# Run specific test file
python -m pytest tests/test_room_allocation.py -v
python -m pytest tests/test_validation.py -v
python -m pytest tests/test_authorization.py -v
python -m pytest tests/test_ui.py -v
```

### Test Results (Latest Run)

| Metric | Value |
|--------|-------|
| **Automated Tests** | 118 |
| **Passed** | 118 (100%) |
| **Failed** | 0 |
| **Skipped** | 0 |
| **Code Coverage** | ~92% |

---

## Demonstration Sequence

For faculty evaluation, follow this sequence:

### 1. Login as Admin or Warden
- Open http://localhost:5000
- Click "Admin" demo button → Login
- Observe sidebar navigation, dashboard stats, quick actions

### 2. View Dashboard and Room Availability
- Admin Dashboard: Note summary cards, occupancy bar, recent allocations table
- Click "Available Rooms" in sidebar → Verify filter by block, "Show full rooms" toggle

### 3. Open Allocation Management
- Click "Allocations" in sidebar
- Verify search box, block filter, status filter, pagination
- Observe action buttons (Reallocate, Cancel) on each row

### 4. Create a Valid Allocation
- Click "New Allocation" button
- Select student, room (note real-time availability preview), start date, optional end date
- Submit → Success flash, redirected to list, new row appears

### 5. Demonstrate Validation
- Try submitting with missing fields → Inline validation errors
- Try end date before start date → Error flash "End date cannot be earlier than start date"
- Try allocating same student again → Error "already has an active room allocation"
- Try allocating to full room → Error "not available"

### 6. Reallocate or Cancel an Allocation
- Click "Reallocate" on a row → Verify current room shown, new room dropdown excludes current
- Select different available room → Submit → Success, room updated in list
- Click "Cancel" on a row → Confirm dialog → Success, row status changes to Cancelled

### 7. Student Restricted View
- Logout → Login as Student (john@student.test)
- Dashboard shows only own profile + allocation
- Click "My Allocation" → Shows own room details only
- Try accessing `/allocation/` → Redirected with "permission" error
- Try accessing another student's allocation → "You can only view your own allocation"

---

## Known Limitations

1. **Concurrency Safety** — SQLite lacks `SELECT FOR UPDATE` and partial unique indexes. Retry logic exists but time-of-check/time-of-use races possible. Requires MySQL/PostgreSQL for production.
2. **Warden Approval Workflow** — Sequence diagram shows approval step; backend auto-approves. UI would need `pending_approval` state.
3. **Past Start Dates** — Allowed by design for admin backdating.
4. **Other Modules** — Complaint, Leave, Fee, Visitor models exist as stubs only; no routes/UI.
5. **Server-Side Pagination** — Implemented but could be enhanced with server-side search for large datasets.
6. **Browser Automation** — Screenshots not captured; manual verification steps documented above.

---

## Relationship: Assignment 8 → Assignment 9

| Aspect | Assignment 8 | Assignment 9 |
|--------|--------------|--------------|
| **Purpose** | Backend implementation + testing | UI design + development |
| **Models** | Created | Reused unchanged |
| **Auth** | Created | Reused unchanged |
| **Routes** | Basic CRUD | Enhanced with search, filter, pagination, better UX |
| **Templates** | Functional but basic | Complete redesign: sidebar layout, macros, accessibility |
| **CSS** | Minimal | Full design system with dark mode, responsive layout |
| **Tests** | Backend-focused | Backend + UI rendering, navigation, accessibility, responsive |

**Assignment 8 files remain completely unmodified.** Assignment 9 is a standalone folder that copies and enhances the necessary code.

---

## Documentation

- [UI Design Document](docs/ui_design.md) — Design rationale, screen descriptions, principles, mapping
- [Requirement Traceability Matrix](docs/requirement_traceability.md) — 38 requirements mapped to screens, files, tests, results

---

## License

Academic submission for BCSE301P Software Engineering coursework.

---

*End of README*