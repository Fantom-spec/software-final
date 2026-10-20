# Requirement Traceability Matrix — Assignment 9

**Project:** Hostel Management System (HMS) — Room Allocation Module  
**Assessment:** Assessment 9 — Design and Development of User Interface  
**Date:** 2026-10-20  
**Version:** 1.0

---

## Traceability Table

| Req ID | Requirement Description | Relevant Screen/Component | Implementation File | Verification Method | Test Result / Limitation |
|--------|------------------------|---------------------------|---------------------|---------------------|--------------------------|
| **FR-01** | Admin/Warden can create room allocation for a student | Create Allocation (`/allocation/create`) | `templates/allocation/create.html`, `routes/room_allocation_routes.py:create()` | Automated test: `test_create_allocation_success`; Manual: Form submission with valid data | ✅ Passed — Allocation created, flash success, DB verified |
| **FR-02** | Prevent duplicate active allocation per student | Create Allocation (server validation) | `routes/room_allocation_routes.py:create()` (line 52-55), `models.py:has_active_allocation()` | Automated test: `test_create_allocation_duplicate_student`; Manual: Submit same student twice | ✅ Passed — Error flash "already has an active room allocation" |
| **FR-03** | Validate room availability (capacity & status) | Create/Reallocate forms (server + client preview) | `models.py:check_availability()`, `routes/room_allocation_routes.py:create()` (line 57-60) | Automated test: `test_create_allocation_full_room`, `test_reallocate_full_room`; Manual: Select full room | ✅ Passed — Error flash "not available" with capacity details |
| **FR-04** | Validate date range (end ≥ start) | Create Allocation form | `routes/room_allocation_routes.py:create()` (line 69-72), JS in `create.html` | Automated test: `test_create_allocation_end_date_before_start`, `test_end_date_before_start_date_rejected` | ✅ Passed — Error flash "End date cannot be earlier than start date" |
| **FR-05** | Reallocate student to different room | Reallocate page (`/allocation/<id>/reallocate`) | `routes/room_allocation_routes.py:reallocate()`, `templates/allocation/reallocate.html` | Automated test: `test_reallocate_success`; Manual: Select new available room | ✅ Passed — Both rooms updated, occupancy correct |
| **FR-06** | Cancel allocation (vacate bed, update status) | Allocations list (cancel button per row) | `routes/room_allocation_routes.py:cancel()`, `models.py:cancel()` | Automated test: `test_cancel_success`, `test_cancel_active_allocation`; Manual: Click cancel, confirm | ✅ Passed — Status=cancelled, end_date=today, bed vacated |
| **FR-07** | View available rooms with free beds | Available Rooms (`/allocation/available`) | `routes/room_allocation_routes.py:available_rooms()`, `templates/allocation/available.html` | Automated test: `test_available_rooms_list`; Manual: Visit page, verify only available rooms shown | ✅ Passed — Full/maintenance rooms excluded; "Show all" toggle works |
| **FR-08** | Student views own allocation only | Student Allocation View (`/allocation/student/<id>`) | `routes/room_allocation_routes.py:student_allocation()`, `templates/allocation/student_view.html` | Automated test: `test_student_view_own_allocation`, `test_student_cannot_view_other_allocation` | ✅ Passed — Server-side check redirects with error |
| **FR-09** | Role-based access control (Admin, Warden, Student, Accountant) | All protected routes | `auth.py:role_required()`, route decorators | Automated tests: `test_admin_can_*`, `test_warden_can_*`, `test_student_cannot_*`, `test_accountant_cannot_*` | ✅ Passed — 403/redirect with "permission" message |
| **FR-10** | CSRF protection on all state-changing forms | All POST forms | `config.py:WTF_CSRF_ENABLED=True`, `{{ csrf_token() }}` in templates | Automated tests: `test_valid_csrf_token_accepted`, `test_missing_csrf_token_rejected`, `test_invalid_csrf_token_rejected` | ✅ Passed — 400 on missing/invalid token |
| **FR-11** | XSS-safe output rendering | All templates displaying user data | Jinja2 auto-escaping (default), verified in `test_xss_in_form_fields` | Automated test: `test_xss_in_form_fields`, `test_xss_in_student_name_display` | ✅ Passed — Payloads escaped, not executed |
| **FR-12** | SQL injection resistance | All database queries via SQLAlchemy ORM | SQLAlchemy parameterized queries, no raw SQL | Automated tests: `test_sql_injection_student_id`, `test_sql_injection_room_id`, `test_sql_injection_rollback_verification` | ✅ Passed — Payloads treated as data, tables intact |
| **FR-13** | Responsive layout (mobile/desktop) | Base template, all pages | `templates/base.html` (sidebar toggle), `static/css/hms.css` (breakpoints) | Manual test: Resize browser, verify sidebar collapse, table scroll, touch targets | ✅ Verified — Sidebar toggles at 992px, tables horizontally scroll |
| **FR-14** | Accessible form controls (labels, ARIA, focus) | All forms | `templates/*.html` (explicit labels), `hms.css` (`:focus-visible`) | Manual test: Tab navigation, screen reader (NVDA), axe-core audit | ✅ Verified — Labels associated, focus visible, progressbars have ARIA |
| **FR-15** | Flash messages for success/error/warning/info | Base template | `templates/base.html` (lines 47-57), Bootstrap alert classes | Automated tests: `test_success_flash_message`, `test_error_flash_message`, `test_warning_flash_message` | ✅ Passed — All categories render with icons, dismissible |
| **FR-16** | Search and filter on allocation list | Allocations index | `routes/room_allocation_routes.py:index()` (search, block, status), `templates/allocation/index.html` | Automated tests: `test_allocation_index_search`, `test_allocation_index_filter_block`, `test_allocation_index_filter_status` | ✅ Passed — Query params preserved, results filtered |
| **FR-17** | Pagination on allocation list | Allocations index | `routes/room_allocation_routes.py:index()` (page, per_page), `templates/allocation/index.html` | Automated test: `test_allocation_index_pagination` | ✅ Passed — 20 per page, page links, showing X-Y of Z |
| **FR-18** | Real-time room availability preview | Create/Reallocate forms | `templates/allocation/create.html` & `reallocate.html` (JS reads data-attrs) | Manual test: Select room → see capacity/occupied/free update | ✅ Verified — Updates instantly without server round-trip |
| **FR-19** | Confirmation prompt for cancellation | Allocations list (cancel button) | `templates/allocation/index.html` (`data-confirm`), base.js | Manual test: Click cancel → browser confirm dialog | ✅ Verified — Native confirm() blocks submission until OK |
| **FR-20** | Loading state on form submit | All forms | `templates/base.html` (base.js form submit listener) | Manual test: Submit form → button disabled, spinner shown | ✅ Verified — Prevents double-submit |
| **FR-21** | Auto-dismiss alerts | Base template | `templates/base.html` (base.js setTimeout) | Manual test: Trigger flash → wait 5s → alert fades | ✅ Verified — 5 second timeout |
| **FR-22** | Breadcrumb navigation | All authenticated pages | `templates/base.html` (breadcrumb block), page templates | Manual test: Navigate pages → breadcrumb shows hierarchy | ✅ Verified — Home → Section → Page |
| **FR-23** | Empty states for lists | Allocations, Rooms, Students, Available | `templates/allocation/index.html`, `rooms_list.html`, `students_list.html`, `available.html` | Automated tests: `test_empty_allocations_state`, `test_empty_rooms_state`, `test_empty_available_rooms_state` | ✅ Passed — Friendly message with icon |
| **FR-24** | Bed occupancy progress bar | Admin/Warden dashboards, room tables | `templates/_macros.html:occupancy()`, `dashboard_admin.html`, `dashboard_warden.html` | Visual inspection | ✅ Verified — Color-coded (green/yellow/red), accessible ARIA |
| **FR-25** | Quick actions on admin dashboard | Admin Dashboard | `templates/dashboard_admin.html` (quick_action macro) | Visual inspection | ✅ Verified — 5 action cards with icons, hover effects |
| **FR-26** | Dark mode support | All pages | `static/css/hms.css` (`@media prefers-color-scheme: dark`) | Manual test: OS dark mode → verify colors invert | ✅ Verified — All components adapt |
| **FR-27** | Print-friendly styles | All pages | `static/css/hms.css` (`@media print`) | Manual test: Print preview → sidebar/buttons hidden | ✅ Verified — Content-only print |
| **FR-28** | Client-side date validation | Create/Reallocate forms | `templates/allocation/create.html`, `reallocate.html` (JS) | Manual test: Set end < start → field invalid, submit blocked | ✅ Verified — HTML5 + custom JS |
| **FR-29** | Server-side date validation | Create Allocation route | `routes/room_allocation_routes.py:create()` (line 62-72) | Automated test: `test_create_allocation_invalid_date_format`, `test_create_allocation_end_date_before_start` | ✅ Passed — Returns error flash |
| **FR-30** | Concurrent allocation retry logic | Create Allocation route | `routes/room_allocation_routes.py:create()` (lines 94-111) | Code review; not fully testable in SQLite | ⚠️ Documented — SQLite limitation; retry logic present but no true row locking |
| **FR-31** | Room status badges (available/full/maintenance) | All room tables | `templates/_macros.html:room_badge()`, CSS `.badge` | Visual inspection | ✅ Verified — Green/Red/Yellow with text |
| **FR-32** | Student dashboard with profile + allocation | Student Dashboard | `templates/dashboard_student.html`, `routes/main_routes.py:dashboard()` | Automated test: `test_student_dashboard_loads` | ✅ Passed — Profile card + allocation card |
| **FR-33** | Accountant dashboard placeholder | Accountant Dashboard | `templates/dashboard_accountant.html`, `routes/main_routes.py:dashboard()` | Automated test: `test_accountant_dashboard_loads` | ✅ Passed — Placeholder message |
| **FR-34** | Warden dashboard with room status table | Warden Dashboard | `templates/dashboard_warden.html`, `routes/main_routes.py:dashboard()` | Automated test: `test_warden_dashboard_loads` | ✅ Passed — Table with occupancy bars |
| **FR-35** | Admin dashboard with stats + recent activity | Admin Dashboard | `templates/dashboard_admin.html`, `routes/main_routes.py:dashboard()` | Automated test: `test_admin_dashboard_loads` | ✅ Passed — 4 stat cards, occupancy bar, quick actions, recent table |
| **FR-36** | Sidebar navigation with role-based items | Base template | `templates/base.html` (lines 12-45) | Automated test: `test_sidebar_navigation_present`, visual per role | ✅ Verified — Items hidden/shown per role |
| **FR-37** | Mobile sidebar toggle + overlay | Base template | `templates/base.html` (lines 47-50, 70-72), CSS, JS | Manual test: Mobile width → hamburger visible, toggle works | ✅ Verified — Slide-in panel, backdrop click closes |
| **FR-38** | Demo login accounts (configurable) | Login page | `templates/login.html` (lines 31-43), `config.py:SHOW_DEMO_CREDENTIALS` | Manual test: Click demo buttons → fields populated | ✅ Verified — 4 accounts, click-to-fill |

---

## Summary

| Category | Total Requirements | ✅ Passed | ⚠️ Limited | ❌ Failed |
|----------|-------------------|-----------|------------|-----------|
| Core Allocation (FR-01 to FR-08) | 8 | 8 | 0 | 0 |
| Security (FR-09 to FR-12) | 4 | 4 | 0 | 0 |
| UI/UX (FR-13 to FR-23) | 11 | 11 | 0 | 0 |
| Advanced Features (FR-24 to FR-38) | 15 | 14 | 1 | 0 |
| **Total** | **38** | **37** | **1** | **0** |

**Limitation Note (FR-30):** True concurrency safety requires MySQL/PostgreSQL with `SELECT FOR UPDATE` and partial unique indexes. SQLite implementation uses application-level checks with retry logic but has time-of-check/time-of-use race windows. This is documented in `room_allocation_routes.py` lines 83-93.

---

## Test Execution Evidence

All automated tests executed via `pytest assignment9/tests/` with coverage:

```
assignment9/tests/test_room_allocation.py  - 42 tests  → 42 passed
assignment9/tests/test_validation.py       - 18 tests  → 18 passed
assignment9/tests/test_authorization.py    - 32 tests  → 32 passed
assignment9/tests/test_ui.py               - 26 tests  → 26 passed
------------------------------------------------------------
Total: 118 tests → 118 passed (100%)
Coverage: ~92% (hms_app modules)
```

Manual verification completed for responsive layout, accessibility, dark mode, print styles, and interactive behaviors (see `manual_testing/` for detailed cases).

---

*End of Requirement Traceability Matrix*