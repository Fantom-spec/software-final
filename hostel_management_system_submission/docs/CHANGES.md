# Change log - consolidation and fixes

Base: the Assessment 9 implementation from the submitted ZIP (it was the more complete one; the two copies of `hms_app/` had diverged). The original ZIP is untouched.

## Consolidation
| Change | Reason |
|---|---|
| One `hms_app/`, one `tests/`, one `requirements.txt` (+ `requirements-test.txt`), one `run.py` | The ZIP held two diverging copies of the app and tests; the A9 test suite is a non-weakened superset of A8's (every A8 test name exists in it) |
| Removed Flask-Login, bcrypt, pytest-flask from the requirements | Declared but never imported/used |
| Removed `venv/`, `.pyc`, `.db`, `app.log`, `.coverage`, `.pytest_cache`, old junit/coverage, old reports, `INITIAL_REVIEW.md`, old screenshots, three overlapping screenshot scripts | Generated/stale files; old reports and evidence contradicted reality (kept in the original ZIP) |

## Application (`hms_app/`)
| File | Change | Reason (defect) |
|---|---|---|
| `auth.py` | stale-session handling; `LoginThrottle`; safe-redirect helper | DEF-023, DEF-022 |
| `routes/auth_routes.py` | POST-only logout; throttle wiring | DEF-019, DEF-022 |
| `config.py` | no hard-coded secret; demo seeding/credentials opt-in; secure-cookie option; date range; throttle settings; `TestConfig` in-memory | DEF-021, DEF-024, DEF-026 |
| `__init__.py` | CSP nonce + security headers; CSRF error page; CLI `seed-demo`, `create-admin`; seeding only on request | DEF-024, DEF-021 |
| `seed.py` (new) | demo data and admin bootstrap moved out of the app factory | DEF-021 |
| `__main__.py`, `../run.py` | debug only if `FLASK_DEBUG=1`; bind 127.0.0.1 | DEF-020 |
| `models.py` | atomic conditional-UPDATE bed counters; CHECK constraints; partial unique index; reallocate takes the new bed first; `db.session.get`; UTC helper | DEF-025, DEF-016, DEF-006, DEF-029 |
| `routes/room_allocation_routes.py` | create re-renders with input kept; date range; deterministic conflict handling (retry loop removed); `show_all` honours block filter; `db.get_or_404` | DEF-028, DEF-026, DEF-025, DEF-027, DEF-029 |
| `templates/base.html` | local assets; nonce on inline scripts; confirm modal; no inline handlers; error alerts persist | DEF-024, DEF-036, DEF-035 |
| `templates/_flashes.html` (new), `layout_authenticated.html` | messages at the top of the page content; role-correct menu; single POST logout; top-bar duplicate removed | DEF-051, DEF-033, DEF-032, DEF-019 |
| `routes/admin_data_routes.py` (new), `templates/admin/*` (new), `rooms_list.html`, `students_list.html`, `__init__.py` | Admin-only forms to add blocks, rooms and students; buttons shown to admins only. Needed because demo seeding became opt-in and nothing else could create data | DEF-052 |
| `templates/csrf_error.html` (new) | readable page for HTTP 400 CSRF failures | DEF-008 |
| `templates/login.html` | demo script only when demo enabled | DEF-021 |
| `templates/allocation/create.html`, `index.html`, `available.html` | keep entered values; `&mdash;` fix; no inline `onchange` | DEF-028, DEF-034, DEF-024 |
| `static/css/hms.css` | `min-width:0` on content column; flex top bar; reserved space for hamburger; logout button style; flash region | DEF-030, DEF-031, DEF-032 |
| `static/vendor/` (new) | Bootstrap and Bootstrap Icons self-hosted (MIT licences included) | DEF-024 |

## Tests (`tests/`)
| File | Change | Reason |
|---|---|---|
| `conftest.py` | import path comment; `make_students` factory | DEF-040 |
| `helpers.py` (new) | own-app helpers (CSRF enabled, no long-lived app context) | genuine CSRF testing |
| `test_csrf.py` (new) | 15 CSRF tests with protection enabled | DEF-038 |
| `test_security.py` (new) | headers/CSP, cookies, secure defaults, seeding, throttling, sessions, redirects | DEF-019..024 |
| `test_allocation_integrity.py` (new) | atomic counters, constraints, lifecycle, dates, filters | DEF-025..028 |
| `test_admin_data_entry.py` (new) | access, validation, duplicates, CSRF, passwords, empty-install flow | DEF-052 |
| `test_ui_behavior.py` (new) | DOM-based UI behavior tests | DEF-041, DEF-032..036, DEF-051 |
| `test_manual_scenarios_dry_run.py` (new) | checks the manual sheet's expected results (automated, not manual evidence) | DEF-044 |
| `test_authorization.py` | logout tests updated to POST; `TestCSRFProtection` repaired to really test CSRF | DEF-019, DEF-015 |
| `test_room_allocation.py`, `test_ui.py` | pagination tests use 25 distinct students; weak UI tests strengthened in place; `db.session.get` | DEF-040, DEF-041, DEF-029 |

No assertion was weakened and no failing test was deleted or skipped.

## Manual test document
| File | Change | Reason |
|---|---|---|
| `scripts/build_manual_test_document.py/.js` (new) | generates `manual_testing/Manual_Test_Document.docx/.pdf` from the case sheet, the execution sheet and the screenshots; shows real results and the tester's own evidence images when recorded | the PDF asks for manual testing with a record of results; the document never marks a case executed unless the sheet says so |
| `scripts/browser/capture_manual_case_screens.mjs`, `scripts/run_manual_doc.sh` (new) | walk the manual cases in order on a fresh demo server and capture the expected screen of every case | reference screenshots; building them exposed DEF-054 and an unexecutable case (REALLOC-06, now corrected) |
| `templates/base.html` | "Processing..." only if the submit was not cancelled; Back-navigation restores the button | DEF-054 |

## Evidence tooling and deliverables
`scripts/run_tests.py`, `scripts/build_reports.py` (reports generated from artifacts; refuses to publish if cited evidence is missing or failed), `scripts/serve_demo.py`, `scripts/run_browser_checks.sh`, `scripts/browser/*` (puppeteer tools), `docs/requirements.csv` (one requirement ID scheme), `assessment8_testing/` (procedure, rewritten manual sheet, defect register, generated reports) and `assessment9_ui/` (rewritten design doc, generated traceability, real screenshots).
