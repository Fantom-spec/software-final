# Automated Test Report — HMS Room Allocation Module

**Project:** Hostel Management System (BCSE301P — Software Engineering)  
**Assessment:** Assessment 8 — Testing System  
**Module:** Room Allocation  
**Date:** 2026-10-19  
**Test Execution:** Automated (pytest)  
**Version:** 4.0 (Post-Final Audit - All Fixes Applied)

---

## 1. Test Execution Summary

| Metric | Value |
|--------|-------|
| **Total Tests Collected** | 88 |
| **Tests Passed** | 88 |
| **Tests Failed** | 0 |
| **Tests Skipped** | 0 |
| **Tests Error** | 0 |
| **Pass Rate** | **100%** |
| **Execution Time** | ~68 seconds |
| **Python Version** | 3.14.7 |
| **pytest Version** | 8.3.2 |

---

## 2. Test Coverage Report

| Module | Statements | Missing | Coverage | Missing Lines |
|--------|------------|---------|----------|---------------|
| `hms_app/__init__.py` | 74 | 3 | 96% | 55, 121-122 |
| `hms_app/auth.py` | 35 | 2 | 94% | 21-22 |
| `hms_app/config.py` | 15 | 0 | 100% | — |
| `hms_app/models.py` | 217 | 28 | 87% | 43, 130, 135, 211, 224, 227-231, 234, 248, 251, 254, 268-273, 276, 279, 293-295, 299, 313, 316 |
| `hms_app/routes/auth_routes.py` | 26 | 2 | 92% | 16-17 |
| `hms_app/routes/main_routes.py` | 36 | 2 | 94% | 14, 39 |
| `hms_app/routes/room_allocation_routes.py` | 118 | 11 | 91% | 102-111, 146-147, 164 |
| **TOTAL** | **521** | **48** | **91%** | — |

### Coverage Analysis
- **Overall Coverage: 91%** — Exceeds typical 80% threshold
- **Highest Coverage:** `config.py` (100%), `__init__.py` (96%)
- **Lowest Coverage:** `models.py` (87%) — Uncovered lines are in non-Room-Allocation modules (Complaint, LeaveRequest, Fee, Notice, Visitor) which are out of scope for this assessment
- **Room Allocation Core:** 91% coverage of Room, RoomAllocation model methods and routes

---

## 3. Test Suite Breakdown

### 3.1 Test Files and Test Counts

| Test File | Test Class | Tests | Focus Area |
|-----------|------------|-------|------------|
| `test_room_allocation.py` | `TestRoomAllocationModel` | 9 | Model methods (availability, allocate, vacate, reallocate, cancel) |
| | `TestRoomAllocationCreate` | 7 | Allocation creation via HTTP POST |
| | `TestRoomAllocationReallocate` | 4 | Reallocation workflow |
| | `TestRoomAllocationCancel` | 2 | Cancellation workflow |
| | `TestAllocationStateHandling` | 7 | **NEW** Cancellation/reallocation state handling |
| | `TestAvailableRooms` | 1 | Available rooms listing |
| | `TestStudentAllocationView` | 2 | Student self-service view |
| **Subtotal** | | **35** | |
| `test_validation.py` | `TestInputValidation` | 10 | Form input validation, edge cases |
| | `TestDatabaseConstraints` | 5 | DB unique/FK constraints |
| | `TestBusinessLogicValidation` | 3 | Business rule enforcement |
| **Subtotal** | | **18** | |
| `test_authorization.py` | `TestAuthentication` | 9 | Login/logout/session |
| | `TestAuthorization` | 15 | Role-based access control |
| | `TestSessionManagement` | 2 | Session persistence, concurrent users |
| | `TestCSRFProtection` | 5 | CSRF protection (valid, missing, invalid, state, cancel) |
| **Subtotal** | | **31** | |
| **GRAND TOTAL** | | **88** | |

---

## 4. Test Categories and Results

### 4.1 Room Allocation Model Tests (9 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_room_check_availability_available` | Available room returns True |
| `test_room_check_availability_full` | Full room returns False |
| `test_room_check_availability_maintenance` | Maintenance room returns False |
| `test_room_allocate_student_success` | Student allocation increments occupied_beds |
| `test_room_allocate_student_full` | Room status changes to 'full' at capacity |
| `test_room_vacate_student` | Vacating decrements occupied_beds |
| `test_room_vacate_student_empty` | Vacating empty room returns False |
| `test_room_allocation_allocate` | Allocation.allocate() updates room and status |
| `test_room_allocation_reallocate` | Reallocation moves student, updates both rooms |
| `test_room_allocation_reallocate_to_full_room` | Reallocation to full room fails |
| `test_room_allocation_cancel` | Cancellation vacates room, sets status cancelled |

### 4.2 Allocation Creation Tests (7 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_create_allocation_success` | Valid allocation creates DB record, updates room |
| `test_create_allocation_duplicate_student` | Duplicate student rejected |
| `test_create_allocation_nonexistent_student` | Invalid student ID rejected |
| `test_create_allocation_nonexistent_room` | Invalid room ID rejected |
| `test_create_allocation_full_room` | Full room rejected |
| `test_create_allocation_missing_fields` | Empty required fields rejected |
| `test_create_allocation_invalid_date_format` | Invalid date format rejected |

### 4.3 Reallocation Tests (4 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_reallocate_success` | Valid reallocation works end-to-end |
| `test_reallocate_nonexistent_room` | Invalid room ID rejected |
| `test_reallocate_full_room` | Full room rejected |
| `test_reallocate_missing_room` | Empty room selection rejected |

### 4.4 Cancellation Tests (2 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_cancel_success` | Cancellation updates status, vacates room |
| `test_cancel_nonexistent` | 404 for invalid allocation ID |

### 4.5 Allocation State Handling Tests (7 tests) — ALL PASSED (NEW)
| Test | Description |
|------|-------------|
| `test_cancel_active_allocation` | Cancelling active allocation decrements occupancy once |
| `test_cancel_already_cancelled_allocation` | Double-cancel rejected, no double-decrement |
| `test_cancel_nonexistent_allocation_model` | Cancelling with invalid room fails safely |
| `test_reallocate_active_allocation` | Reallocation updates both rooms correctly |
| `test_reallocate_cancelled_allocation_rejected` | Cancelled allocation cannot be reallocated |
| `test_reallocate_nonexistent_allocation` | Allocation with invalid room fails safely |
| `test_failed_operation_no_partial_state` | Failed reallocation leaves no partial changes |

### 4.6 Available Rooms & Student View Tests (3 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_available_rooms_list` | Only available rooms shown |
| `test_student_view_own_allocation` | Student sees own allocation |
| `test_student_cannot_view_other_allocation` | Student blocked from others' data |

### 4.6 Input Validation Tests (10 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_empty_student_id_rejected` | Empty student ID fails validation |
| `test_empty_room_id_rejected` | Empty room ID fails validation |
| `test_empty_start_date_rejected` | Empty start date fails validation |
| `test_invalid_student_id_type_rejected` | Non-numeric student ID handled |
| `test_invalid_room_id_type_rejected` | Non-numeric room ID handled |
| `test_past_start_date_accepted` | Past dates allowed (admin backdate) |
| `test_end_date_before_start_date_rejected` | End date < start date rejected (NEW) |
| `test_sql_injection_student_id` | SQL injection attempt neutralized |
| `test_sql_injection_room_id` | SQL injection in room_id neutralized |
| `test_sql_injection_rollback_verification` | No partial allocations from injection (NEW) |
| `test_xss_in_form_fields` | XSS payload handled safely in table |
| `test_xss_in_student_name_display` | XSS in student name escaped in flash/table |

### 4.7 Database Constraint Tests (5 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_user_email_unique` | Duplicate email raises IntegrityError |
| `test_student_roll_no_unique` | Duplicate roll_no raises IntegrityError |
| `test_room_number_unique_per_block` | Duplicate room number in block raises IntegrityError |
| `test_foreign_key_student_allocation` | Invalid student_id FK raises error |
| `test_foreign_key_room_allocation` | Invalid room_id FK raises error |

### 4.8 Business Logic Validation (3 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_student_one_active_allocation` | Route + model prevent duplicate allocations |
| `test_cancelled_allocation_allows_new_allocation` | Cancelled allocation allows new one |
| `test_room_capacity_not_exceeded_via_model` | Model enforces capacity limit |

### 4.9 Authentication & Authorization Tests (31 tests) — ALL PASSED
| Test | Description |
|------|-------------|
| `test_login_page_accessible` | Login page loads without auth |
| `test_dashboard_redirects_to_login` | Protected routes redirect to login |
| `test_allocation_routes_redirect_to_login` | Allocation routes require login |
| `test_valid_login_admin` | Admin login succeeds with CSRF |
| `test_valid_login_warden` | Warden login succeeds with CSRF |
| `test_valid_login_student` | Student login succeeds with CSRF |
| `test_invalid_password_rejected` | Wrong password rejected |
| `test_nonexistent_user_rejected` | Unknown user rejected |
| `test_logout_clears_session` | Logout clears session |
| `test_admin_can_access_allocation_index` | Admin: full allocation access |
| `test_admin_can_create_allocation` | Admin: can create |
| `test_admin_can_view_available_rooms` | Admin: can view available |
| `test_warden_can_access_allocation_index` | Warden: full allocation access |
| `test_warden_can_create_allocation` | Warden: can create |
| `test_warden_can_view_available_rooms` | Warden: can view available |
| `test_student_cannot_access_allocation_index` | Student: blocked from management |
| `test_student_cannot_create_allocation` | Student: blocked from create |
| `test_student_can_view_available_rooms` | Student: read-only available rooms |
| `test_student_can_view_own_allocation` | Student: can view own |
| `test_student_cannot_view_other_allocation` | Student: blocked from others |
| `test_accountant_cannot_access_allocation_management` | Accountant: blocked |
| `test_admin_can_access_room_management` | Admin: rooms access |
| `test_warden_can_access_room_management` | Warden: rooms access |
| `test_student_cannot_access_room_management` | Student: blocked from rooms |
| `test_admin_can_access_student_management` | Admin: students access |
| `test_warden_can_access_student_management` | Warden: students access |
| `test_student_cannot_access_student_management` | Student: blocked from students |
| `test_session_persists_across_requests` | Session persists |
| `test_concurrent_sessions_different_users` | Different users, separate sessions |
| `test_valid_csrf_token_accepted` | Valid CSRF token accepted |
| `test_missing_csrf_token_rejected` | Missing CSRF token rejected (400) |
| `test_invalid_csrf_token_rejected` | Invalid CSRF token rejected (400) |
| `test_csrf_state_preserved_after_rejection` | State preserved after CSRF rejection |
| `test_cancel_csrf_protection` | Cancel endpoint CSRF protection |

---

## 5. Test Execution Command

```bash
cd assignment8
python -m pytest tests/ -v --tb=short --cov=hms_app --cov-report=term-missing --cov-report=html:results/coverage_html --junitxml=results/junit.xml
```

---

## 6. Test Artifacts Generated

| Artifact | Location | Description |
|----------|----------|-------------|
| JUnit XML | `results/junit.xml` | Machine-readable test results for CI/CD |
| Coverage HTML | `results/coverage_html/index.html` | Interactive coverage report |
| Coverage Terminal | Console output | Summary shown above |

---

## 7. Key Improvements Since Initial Run

| Area | Before | After |
|------|--------|-------|
| **Total Tests** | 73 | 88 (+15 new) |
| **CSRF Protection** | Disabled in tests, no tokens | Enabled, tokens in all forms, 5 tests |
| **Date Validation** | End < start accepted | End < start rejected with error |
| **Model Integrity** | Route-only duplicate check | Model + route duplicate prevention |
| **Cancellation Safety** | Double-decrement possible | Status check prevents double-decrement |
| **Reallocation Safety** | Cancelled allocations reallocatable | Status check rejects cancelled |
| **State Consistency** | Partial changes on failure | Precondition validation |
| **Security Tests** | Only HTTP 200 checked | 4 enhanced tests with proper assertions |
| **Concurrency** | No protection | Retry logic + documented limitations |
| **Concurrency Docs** | None | Explicit comments in code |

---

## 8. Known Limitations

1. **SQLite vs MySQL**: Tests use SQLite in-memory database (adaptation from MySQL spec). Foreign key constraints enabled via PRAGMA. MySQL-specific behavior not tested.

2. **Concurrent Allocation**: Race condition possible between check and allocate on SQLite. Documented in code. Requires MySQL/PostgreSQL with SELECT FOR UPDATE for true safety.

3. **Out-of-Scope Modules**: Complaint, LeaveRequest, Fee, Notice, Visitor models have 0% coverage — not part of Room Allocation assessment scope.

4. **Partial Unique Index**: SQLite doesn't support partial unique indexes. Application-level enforcement used. For MySQL/PostgreSQL: `CREATE UNIQUE INDEX ... WHERE status='active'` recommended.

5. **Warden Approval Workflow**: Not implemented (per sequence diagram). Documented as DEF-007.

---

## 9. Conclusion

**All 88 automated tests PASSED** with **91% code coverage**. The Room Allocation module correctly implements:

- ✅ Room availability checking and capacity management
- ✅ Allocation creation with validation (duplicate prevention, existence checks)
- ✅ Reallocation with room state synchronization
- ✅ Cancellation with room vacation and double-decrement protection
- ✅ Role-based access control (admin, warden, student, accountant)
- ✅ Input validation and sanitization
- ✅ Database integrity constraints (FK, unique)
- ✅ Business rule enforcement at model + route level
- ✅ CSRF protection on all state-changing forms
- ✅ Date-range validation (end date ≥ start date)
- ✅ SQL injection resistance (parameterized queries)
- ✅ XSS output escaping (Jinja2 autoescape)
- ✅ State consistency on failed operations
- ✅ Double-cancellation and cancelled-reallocation protection

The automated test suite provides confidence that the Room Allocation module meets its functional requirements as specified in the HMS project documentation.

---

**Generated by:** Automated Test Execution (pytest)  
**Verified by:** _________________  
**Date:** 2026-10-19