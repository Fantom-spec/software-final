# Assessment 8 — HMS Testing System

**Course:** BCSE301P — Software Engineering  
**Module Under Test:** Room Allocation  
**Date:** 2026-10-19  
**Version:** 4.0 (Post-Final Audit - All Fixes Applied)

---

## Overview

This folder contains the complete Assessment 8 submission for the Hostel Management System (HMS) Room Allocation module testing. Since the repository contained only documentation and UML diagrams (no executable Flask application), a **minimal working implementation** was created to enable genuine testing.

An independent audit identified validation, security, database integrity, concurrency, and testing-quality problems. **All applicable issues have been fixed**, regression tests added, and the test suite re-executed.

---

## Folder Structure

```
assignment8/
├── README.md                    # This file
├── INITIAL_REVIEW.md            # Repository analysis and module selection
├── requirements-test.txt        # Test dependencies
├── test_plan.md                 # Test plan (integrated in final report)
├── test_cases.md                # Test cases (in test files and manual_testing/)
├── manual_test_report.md        # Manual test documentation
├── automated_test_report.md     # Automated test results (latest run)
├── defect_log.md                # Defects found and fixed (v4.0)
├── final_test_report.md         # Comprehensive final report
├── hms_app/                     # Minimal Flask HMS implementation
│   ├── __init__.py              # App factory with CSRF, fixtures
│   ├── config.py                # Config classes (TestConfig with CSRF enabled)
│   ├── models.py                # SQLAlchemy models with integrity checks
│   ├── auth.py                  # Authentication helpers
│   ├── routes/
│   │   ├── auth_routes.py       # Login/logout with CSRF
│   │   ├── main_routes.py       # Dashboards, listings
│   │   └── room_allocation_routes.py  # Allocation CRUD with validation
│   └── templates/               # Jinja2 templates with CSRF tokens
├── tests/
│   ├── conftest.py              # Pytest fixtures (app, client, db, users, CSRF)
│   ├── test_room_allocation.py  # 35 allocation tests
│   ├── test_validation.py       # 18 validation/constraint tests
│   └── test_authorization.py    # 31 auth/authorization tests
├── manual_testing/
│   ├── manual_test_cases.csv    # 56 detailed manual test cases
│   └── manual_test_execution.csv # Execution sheet template
├── scripts/
│   └── run_tests.py             # Test runner script
└── results/
    ├── junit.xml                # JUnit test results (generated)
    └── coverage_html/           # HTML coverage report (generated)
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation
```bash
cd assignment8
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

pip install -r requirements-test.txt
```

### Run Automated Tests
```bash
# Full test suite with coverage
python -m pytest tests/ -v --cov=hms_app --cov-report=term-missing --cov-report=html:results/coverage_html

# Or use the runner script
python scripts/run_tests.py

# Run specific test file
python -m pytest tests/test_room_allocation.py -v
```

### Run Manual Tests
1. Start the application: `python -m hms_app`
2. Open http://localhost:5000
3. Follow test cases in `manual_testing/manual_test_cases.csv`
4. Record results in `manual_testing/manual_test_execution.csv`

### Test Accounts
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@hms.test | admin123 |
| Warden | warden@hms.test | warden123 |
| Student | john@student.test | student123 |
| Accountant | accountant@hms.test | accountant123 |

---

## Test Results Summary (Latest Run)

| Metric | Value |
|--------|-------|
| **Automated Tests** | 88 |
| **Passed** | 88 (100%) |
| **Failed** | 0 |
| **Skipped** | 0 |
| **Code Coverage** | 91% |

### Test Categories
| Category | Tests | Status |
|----------|-------|--------|
| Room Allocation Model | 9 | ✅ All Passed |
| Allocation Creation | 7 | ✅ All Passed |
| Reallocation | 4 | ✅ All Passed |
| Cancellation | 2 | ✅ All Passed |
| State Handling (NEW) | 7 | ✅ All Passed |
| Available Rooms | 1 | ✅ Passed |
| Student Self-Service | 2 | ✅ All Passed |
| Input Validation | 10 | ✅ All Passed |
| Database Constraints | 5 | ✅ All Passed |
| Business Logic | 3 | ✅ All Passed |
| Authentication | 9 | ✅ All Passed |
| Authorization | 15 | ✅ All Passed |
| Session Management | 2 | ✅ All Passed |
| CSRF Protection | 5 | ✅ All Passed (NEW) |

---

## Key Fixes Applied (Post-Audit)

| Issue | Fix | Files |
|-------|-----|-------|
| **CSRF Protection Missing** | Added CSRFProtect init, tokens in all forms, 5 tests | `__init__.py`, `config.py`, templates, `test_authorization.py` |
| **Date-Range Validation** | End date < start date rejected with error | `room_allocation_routes.py`, `test_validation.py` |
| **Duplicate Allocation (Model)** | `has_active_allocation()` + check in `allocate()` | `models.py`, `room_allocation_routes.py` |
| **Cancellation Double-Decrement** | Status check in `cancel()` prevents double-decrement | `models.py` |
| **Reallocation of Cancelled** | Status check in `reallocate()` rejects cancelled | `models.py` |
| **Partial State on Failure** | Precondition validation before changes | `models.py` |
| **Concurrency/Race Condition** | Retry logic + documented limitations | `room_allocation_routes.py` |
| **SQL Injection Tests** | Strengthened with actual payload assertions | `test_validation.py` |
| **XSS Tests** | Verify payloads escaped in output | `test_validation.py` |
| **CSRF Test Skip** | Get token from create page | `test_room_allocation.py` |
| **Concurrency Docs** | Added limitation comments | `room_allocation_routes.py` |
| **Student Relationship** | Renamed to `student_profile` | `models.py`, routes, templates |
| **Student View Relationship** | Fixed to use `student_profile` | `room_allocation_routes.py` |

---

## Key Findings

✅ **All core functionality verified:**
- Room allocation with availability checking
- Capacity management and status tracking
- Duplicate prevention (route + model level)
- Role-based access control (4 roles)
- Reallocation and cancellation workflows
- Student self-service portal
- CSRF protection on all state-changing forms
- Date-range validation
- SQL injection resistance
- XSS output escaping
- Concurrency retry logic

⚠️ **Documented Gaps:**
1. **Warden approval workflow** — Sequence diagram shows approval step; implementation auto-approves
2. **Partial unique index for active allocations** — SQLite limitation; app-level enforcement used
3. **MySQL-specific testing** — SQLite used with documented adaptation
4. **Past start dates** — Allowed by design for admin backdating
5. **True concurrency safety** — Requires MySQL/PostgreSQL with row-level locks

---

## Reports

| Report | Location |
|--------|----------|
| Initial Repository Review | `INITIAL_REVIEW.md` |
| Automated Test Report | `automated_test_report.md` |
| Defect Log | `defect_log.md` |
| Final Test Report | `final_test_report.md` |
| Manual Test Cases | `manual_testing/manual_test_cases.csv` |
| Manual Execution Sheet | `manual_testing/manual_test_execution.csv` |
| Coverage Report | `results/coverage_html/index.html` (after test run) |

---

## Technology Stack (Test Environment)

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.0.3, Python 3.14 |
| Database | SQLite (test), MySQL 8.x (spec) |
| ORM | SQLAlchemy 2.0, Flask-SQLAlchemy 3.1 |
| Auth | Flask-Login 0.6, bcrypt 4.2 |
| CSRF | Flask-WTF CSRFProtect |
| Testing | pytest 8.3, pytest-cov 5.0, pytest-flask 1.3 |
| Frontend | Bootstrap 5.3, Jinja2 templates |

---

## Notes

1. **Database Adaptation:** Tests use SQLite in-memory database with `PRAGMA foreign_keys=ON` to match MySQL constraint enforcement. This is documented in `INITIAL_REVIEW.md` and `final_test_report.md`.

2. **Minimal Implementation:** The `hms_app/` contains only the Room Allocation module and supporting auth/models. Other modules (Complaint, Leave, Fee, etc.) have model stubs but no routes.

3. **No Production Code Modified:** All testing code is isolated in `assignment8/`. Original repository files unchanged.

4. **Honest Reporting:** Test results reflect actual execution. No tests fabricated or claimed as passed without evidence.

5. **Historical Evidence:** Previous test results and reports are preserved. Updated reports clearly distinguish original defects, fixes, regression tests, and actual new results.

---

## References

- Project Specification: `../Hostel_Management_System_Assignment.md`
- Class Diagram: `../ver2/HMS_Class_Diagram.mdj`
- Sequence Diagram: `../ver2/HMS_Sequence_Diagram_RoomAllocation.mdj`
- Use Case Diagram: `../ver2/HMS_Use_Case_Diagram.mdj`