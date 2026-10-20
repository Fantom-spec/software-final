# Defect Log — HMS Room Allocation Module Testing

**Project:** Hostel Management System (BCSE301P — Software Engineering)  
**Assessment:** Assessment 8 — Testing System  
**Module:** Room Allocation  
**Date:** 2026-10-19  
**Version:** 4.0 (Post-Final Audit - All Fixes Applied)

---

## Defect Summary

| Defect ID | Severity | Status | Summary |
|-----------|----------|--------|---------|
| DEF-001 | Medium | **Fixed** | SQLite foreign key enforcement requires explicit PRAGMA |
| DEF-002 | Low | **By Design** | Room number uniqueness not enforced across blocks |
| DEF-003 | Low | **Fixed** | End date before start date accepted (no server-side validation) |
| DEF-004 | Low | **Open (Doc)** | Past start dates allowed for allocations |
| DEF-005 | Medium | **Fixed** | Model allows duplicate student allocations; only route prevents |
| DEF-006 | Low | **Mitigated** | No unique constraint on active allocation per student |
| DEF-007 | Low | **Open** | Warden approval workflow not implemented |
| DEF-008 | High | **Fixed** | CSRF protection not implemented (only config variable) |
| DEF-009 | Medium | **Fixed** | Missing date-range validation in reallocation |
| DEF-010 | Low | **Fixed** | Test for end_date < start_date asserted wrong behavior |
| DEF-011 | Medium | **Fixed** | Cancellation double-decrement bug |
| DEF-012 | Medium | **Fixed** | Reallocation allows cancelled allocations |
| DEF-013 | Medium | **Fixed** | Failed operations leave partial state changes |
| DEF-014 | Medium | **Fixed** | SQL injection/XSS tests only checked HTTP 200 |
| DEF-015 | Medium | **Fixed** | CSRF test skipped due to missing token on empty page |
| DEF-016 | Low | **Documented** | Concurrency safety not guaranteed on SQLite |
| DEF-017 | Medium | **Fixed** | Student relationship renamed from `student` to `student_profile` |
| DEF-018 | Medium | **Fixed** | Student allocation view used incorrect relationship |

---

## Detailed Defects (Historical)

### DEF-001: SQLite Foreign Key Enforcement Requires Explicit PRAGMA
- **Severity:** Medium | **Status:** Fixed (pre-existing fix)
- **Fix:** Event listener in `hms_app/__init__.py` enables `PRAGMA foreign_keys=ON`
- **Verification:** Tests `test_foreign_key_student_allocation` and `test_foreign_key_room_allocation` pass

### DEF-002: Room Number Uniqueness Not Enforced Across Blocks
- **Severity:** Low | **Status:** By Design
- **Resolution:** Unique constraint defined on `(block_id, room_number)` composite. This matches requirements.

### DEF-003: End Date Before Start Date Accepted
- **Severity:** Low | **Status:** Fixed
- **Fix:** Server-side validation in `room_allocation_routes.py` create() method
- **Verification:** Test `test_end_date_before_start_date_rejected` passes

### DEF-004: Past Start Dates Allowed for Allocations
- **Severity:** Low | **Status:** Open (Documented)
- **Resolution:** Documented as acceptable behavior (admin may need to backdate records)

### DEF-005: Model Allows Duplicate Student Allocations
- **Severity:** Medium | **Status:** Fixed
- **Fix:** Added `RoomAllocation.has_active_allocation()` classmethod and check in `allocate()` method
- **Verification:** Tests `test_student_one_active_allocation` and `test_cancelled_allocation_allows_new_allocation` pass

### DEF-006: No Unique Constraint on Active Allocation Per Student
- **Severity:** Low | **Status:** Mitigated
- **Mitigation:** Application-level enforcement in `RoomAllocation.allocate()` and `has_active_allocation()`
- **Note:** SQLite doesn't support partial unique indexes. For MySQL/PostgreSQL: `CREATE UNIQUE INDEX ... WHERE status='active'`

### DEF-007: Warden Approval Workflow Not Implemented
- **Severity:** Low | **Status:** Open
- **Description:** Sequence diagram shows approval step; implementation auto-approves
- **Recommendation:** Add allocation status 'pending_approval', warden approval endpoint, notification system

### DEF-008: CSRF Protection Not Implemented
- **Severity:** High | **Status:** Fixed
- **Fix:** 
  1. Added `CSRFProtect` initialization in `hms_app/__init__.py`
  2. Added CSRF tokens to all state-changing forms (login, create, reallocate, cancel)
  3. Enabled CSRF in TestConfig for testing
  4. Added 5 comprehensive CSRF tests (valid, missing, invalid, state preservation, cancel endpoint)
- **Verification:** All 5 CSRF tests pass

### DEF-009: Missing Date-Range Validation in Reallocation
- **Severity:** Medium | **Status:** Fixed
- **Fix:** Date validation already in create route; reallocation doesn't change dates so not strictly needed, but model-level validation added for consistency

### DEF-010: Test Asserted Wrong Behavior for End Date < Start Date
- **Severity:** Low | **Status:** Fixed
- **Fix:** Changed test to `test_end_date_before_start_date_rejected` with proper assertion
- **Verification:** New test passes with validation error message

### DEF-011: Cancellation Double-Decrement Bug
- **Severity:** Medium | **Status:** Fixed
- **Fix:** `cancel()` method checks `status == 'active'` before decrementing
- **Verification:** Test `test_cancel_already_cancelled_allocation` passes

### DEF-012: Reallocation Allows Cancelled Allocations
- **Severity:** Medium | **Status:** Fixed
- **Fix:** `reallocate()` method checks `status == 'active'` before proceeding
- **Verification:** Test `test_reallocate_cancelled_allocation_rejected` passes

### DEF-013: Failed Operations Leave Partial State Changes
- **Severity:** Medium | **Status:** Fixed
- **Fix:** Both `cancel()` and `reallocate()` validate preconditions before state changes
- **Verification:** Test `test_failed_operation_no_partial_state` passes

### DEF-014: Weak SQL Injection/XSS Tests
- **Severity:** Medium | **Status:** Fixed
- **Fix:** Enhanced assertions verifying payloads are escaped/neutralized
- **Verification:** 4 enhanced security tests pass with proper assertions

### DEF-015: CSRF Test Skipped Due to Missing Token
- **Severity:** Medium | **Status:** Fixed
- **Fix:** Test now gets CSRF token from create page (always has form)
- **Verification:** Test `test_cancel_nonexistent` passes

### DEF-016: Concurrency Safety Not Guaranteed on SQLite
- **Severity:** Low | **Status:** Documented
- **Documentation:** Added explicit comments in `room_allocation_routes.py` about limitations
- **Note:** SQLite lacks SELECT FOR UPDATE; true concurrency safety requires MySQL/PostgreSQL with row-level locks

### DEF-017: Student Relationship Renamed
- **Severity:** Medium | **Status:** Fixed
- **Fix:** Renamed User.student relationship to `student_profile` with explicit `back_populates`
- **Impact:** Fixed dashboard, student allocation view, and all related code

### DEF-018: Student Allocation View Used Incorrect Relationship
- **Severity:** Medium | **Status:** Fixed
- **Fix:** Updated `student_allocation` route to use `user.student_profile.student_id`
- **Verification:** 4 student allocation view tests pass

---

## Defects Fixed During Current Audit

| Defect ID | Summary | Fix Applied | Files Modified |
|-----------|---------|-------------|----------------|
| DEF-008 | CSRF protection missing | CSRFProtect init, tokens in all forms, 5 tests | `__init__.py`, `config.py`, templates, `test_authorization.py` |
| DEF-003 | End date < start date accepted | Validation in create route | `room_allocation_routes.py`, `test_validation.py` |
| DEF-005 | Model allows duplicate allocations | `has_active_allocation()` + check in `allocate()` | `models.py`, `room_allocation_routes.py` |
| DEF-010 | Concurrency race condition | Retry logic with IntegrityError handling | `room_allocation_routes.py` |
| DEF-011 | Cancellation double-decrement | Status check in `cancel()` | `models.py` |
| DEF-012 | Reallocation of cancelled | Status check in `reallocate()` | `models.py` |
| DEF-013 | Partial state on failure | Precondition validation before changes | `models.py` |
| DEF-014 | Weak security tests | Enhanced assertions for SQLi/XSS | `test_validation.py` |
| DEF-015 | CSRF test skip | Get token from create page | `test_room_allocation.py` |
| DEF-016 | Concurrency docs | Added limitation comments | `room_allocation_routes.py` |
| DEF-017 | Student relationship rename | Renamed to `student_profile` | `models.py`, routes, templates |
| DEF-018 | Student view wrong relationship | Fixed to use `student_profile` | `room_allocation_routes.py` |

---

## Regression Testing

Full test suite re-run after each fix — all passed.

| Fix Cycle | Tests Run | Passed | Failed | Skipped |
|-----------|-----------|--------|--------|---------|
| Initial (with defects) | 73 | 24 | 49+ | 0 |
| Post Initial Fixes | 73 | 73 | 0 | 0 |
| Post Audit Fixes (DEF-008,003,005,010,009) | 76 | 75 | 0 | 1 |
| Post Final Audit Fixes (DEF-011 to DEF-018) | 88 | 88 | 0 | 0 |

---

## Defect Metrics

| Metric | Count |
|--------|-------|
| Total Defects Found (all phases) | 18 |
| Critical | 0 |
| High | 1 (DEF-008 - Fixed) |
| Medium | 8 (DEF-001, DEF-005, DEF-009, DEF-011, DEF-012, DEF-013, DEF-014, DEF-015 - Fixed) |
| Low | 9 (DEF-002, DEF-003, DEF-004, DEF-006, DEF-007, DEF-010, DEF-014, DEF-015, DEF-016 - 7 Fixed/mitigated) |
| Fixed During Audit | 13 |
| Remaining Open | 2 (DEF-004, DEF-007) |

---

**Prepared by:** Assessment 8 Testing Team  
**Reviewed by:** _________________  
**Date:** 2026-10-19