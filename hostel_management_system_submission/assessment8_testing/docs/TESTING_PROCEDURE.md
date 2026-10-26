# Testing procedure - Room Allocation module (Assessment 8)

Tools: **pytest** (test runner), **pytest-cov / coverage.py** (coverage), **BeautifulSoup** (HTML assertions), **Flask test client** (drives the real application), **puppeteer-core + headless Chrome** (browser checks), and a normal **web browser with DevTools** (manual testing).

Commands are shown for Linux/macOS (bash). On Windows PowerShell use `py -m venv venv; venv\Scripts\Activate.ps1`, and `$env:NAME="value"; python ...` instead of `NAME=value python ...`.

## 1. One-time setup

1. Install Python 3.10 or newer (the evidence in `results/` was produced with the version listed in `results/environment.txt`).
2. From the project root:
   ```
   python -m venv venv
   source venv/bin/activate            # Windows: venv\Scripts\activate
   pip install -r requirements-test.txt
   ```
3. Confirm: `python -m pytest --version` prints pytest 8.x.

## 2. What is being tested

The Room Allocation module and what it depends on: allocate / reallocate / cancel, listing and filtering, available rooms, the student's own view, role-based access, login/logout/session handling and CSRF. Requirements are `RA-01...RA-15` (module) and `UI-01...UI-06` (interface) in `docs/requirements.csv`. `assessment8_testing/requirements_traceability.md` maps each requirement to its tests.

## 3. Starting the application for manual testing

The application never creates accounts or data by itself (an administrator adds blocks, rooms and students through the Rooms and Students pages). For testing, use the demo server, which uses a throw-away database (deleted when you stop it):

```
python scripts/serve_demo.py                   # http://127.0.0.1:5000, demo data, NO allocations yet
```
Variants (set before the command):

| Purpose | Command |
|---|---|
| Normal manual run (cases in order) | `DEMO_ALLOCATIONS=0 python scripts/serve_demo.py` |
| Lockout case AUTH-09 | `LOGIN_MAX_ATTEMPTS=5 DEMO_ALLOCATIONS=0 python scripts/serve_demo.py` |
| Show demo accounts on the login page (NOT for SEC-07) | `SHOW_DEMO_CREDENTIALS=1 python scripts/serve_demo.py` |

Demo accounts: `admin@hms.test / admin123`, `warden@hms.test / warden123`, `john@student.test / student123` (also jane, bob, alice, carlos, dana @student.test), `accountant@hms.test / accountant123`. Students have ids 1-6 in that order (John=1 ... Dana=6). **Restart the server (Ctrl+C, run again) for a clean database before each full pass.**

## 4. Manual testing - step by step

**Manual Test Document:** `assessment8_testing/manual_testing/Manual_Test_Document.docx` (and a `.pdf` copy for printing) contains the environment form, test data, procedure, every case with its steps, expected result and a *reference screenshot of the expected screen*, a blank result box per case, a summary, a defect table and a sign-off block. Execute from it (or from the CSV) and record results in `manual_test_execution.csv`; regenerate the document afterwards and it shows your results and your own evidence screenshots. The reference screenshots are produced by a script and are **not** evidence that a case was executed.

Files: cases `assessment8_testing/manual_testing/manual_test_cases.csv` (readable copy: `manual_test_cases.md`), results sheet `manual_test_execution.csv`.

1. Start the server (section 3). Open `http://127.0.0.1:5000` in Chrome or Firefox.
2. Create the folder `assessment8_testing/manual_testing/evidence/` for screenshots.
3. Execute the cases **in the order they appear in the sheet** (later cases depend on data created by earlier ones; each case lists its preconditions). The minimum set is every case with `Priority = P1`; P2/P3 are recommended.
4. For each case: perform the steps exactly; compare what you see with **Expected Result**; take a screenshot of the decisive screen (file name = the case id, e.g. `ALLOC-05.png`).
5. Cases marked **UI + browser DevTools** need F12: *Elements* tab to edit or delete a form field (right-click the element > Delete element / Edit attribute), *Network* tab to read the HTTP status of a request, *Console* tab to run the provided `fetch(...)` snippet.
6. Record the result in `manual_test_execution.csv`, one row per case:
   - `Executed (Y/N)` = Y; `Status` = **Pass** (actual = expected), **Fail** (differs) or **Blocked** (could not run; say why);
   - `Actual Result` = what you really saw (for a Pass, a short factual description - not just "OK");
   - `Evidence` = the screenshot file name; `Executed By` = your name; `Date` = date of execution (YYYY-MM-DD); `Build / commit tested` = e.g. the folder/zip name or git commit.
7. If a case fails: add a row to `assessment8_testing/defects.csv` with a new id (continue after the last `DEF-0xx`), severity, status `Open`, `verification` = `none`, and put that id in the `Defect ID` column of the sheet. Do **not** mark a defect Fixed without a test or browser check that proves it.
8. Never record a result you did not observe. Cases you did not run stay `Not Executed` with empty result columns. The report builder rejects an executed row that lacks Actual Result, Executed By or Date, and a Not-Executed row that has data.
9. When finished (or at any point), regenerate the reports and the document: `python scripts/build_reports.py` and `python scripts/build_manual_test_document.py` (needs Node.js; first `cd scripts/browser && npm install`). To refresh the reference screenshots as well: `scripts/run_manual_doc.sh`. This updates `manual_testing/manual_test_report.md`, `final_test_report.md` and the traceability tables from your sheet.

## 5. Automated testing - step by step

1. Activate the virtual environment (section 1).
2. Run everything and produce all evidence in one go:
   ```
   python scripts/run_tests.py
   ```
   It runs `pytest` with JUnit XML and branch coverage, stores `results/junit.xml`, `results/coverage.xml`, `results/pytest_output.txt`, `results/environment.txt`, `results/run_info.json`, then runs `scripts/build_reports.py`.
3. Read the result: the last line of `results/pytest_output.txt` states passed/failed counts; each failure prints the assertion and the line. Exit code 0 = all passed.
4. Useful variations (no evidence files written):

   | Goal | Command |
   |---|---|
   | One file | `python -m pytest tests/test_csrf.py -v` |
   | One test | `python -m pytest "tests/test_allocation_integrity.py::TestAtomicCounters::test_stale_object_cannot_oversubscribe" -v` |
   | By keyword | `python -m pytest -k "cancel" -v` |
   | Security / UI groups | `python -m pytest -m security` / `-m ui` |
   | Stop at first failure | `python -m pytest -x` |
   | HTML coverage view | `python -m pytest --cov=hms_app --cov-branch --cov-report=html` then open `htmlcov/index.html` |

5. What the test files cover:

   | File | Focus |
   |---|---|
   | `test_room_allocation.py` | allocate / reallocate / cancel through routes and models, lists, dashboards, student view |
   | `test_allocation_integrity.py` | atomic bed counters, DB constraints, lifecycle consistency, date range, form retention, filters |
   | `test_authorization.py` | role-based access, login/logout, sessions, repaired CSRF tests |
   | `test_csrf.py` | CSRF with protection **enabled** (own app instance): missing, forged, foreign-session tokens; logout |
   | `test_security.py` | headers/CSP, cookie flags, secure defaults, seeding, throttling, stale sessions, safe redirects |
   | `test_admin_data_entry.py` | admin-only add block/room/student: access, validation of every field, duplicates, CSRF, password handling, empty-install-to-first-allocation flow |
   | `test_validation.py` | input validation, DB constraints, SQL-injection/XSS handling |
   | `test_ui.py`, `test_ui_behavior.py` | rendered pages parsed as HTML: navigation per role, forms, labels, modal, feedback, no leaked markup |
   | `test_manual_scenarios_dry_run.py` | scripted walk-through confirming the manual sheet's expected results (automated; NOT manual evidence) |

6. **Why the tests can be trusted**: general fixtures disable CSRF for convenience, but CSRF behavior is tested on separate app instances with CSRF enabled; tests that guard a defect were checked to fail when the defect is re-introduced (mutation check, e.g. re-enabling the old non-atomic bed counter makes `test_stale_object_cannot_oversubscribe` fail).

## 6. Browser checks (real browser, automated)

Needs Node.js 18+ and network access to download the npm packages and a Chromium build:
```
scripts/run_browser_checks.sh
```
It starts the demo server, drives headless Chrome through `scripts/browser/verify_ui.mjs` (layout at 320/390/768/1366 px, mobile drawer, POST logout, confirmation modal, validation behavior, CSP violations, console errors), writes `assessment9_ui/docs/browser_verification.txt`, then captures screenshots into `assessment9_ui/screenshots/`. Rebuild the reports afterwards: `python scripts/build_reports.py`.

## 7. Comparing actual with expected results and reporting defects

- Automated: a test passes only if every assertion (the *expected* result) holds for the *actual* behavior; failures show both values. Any failure is investigated and recorded in `defects.csv`.
- Manual: the `Actual Result` column against `Expected Result` in the case sheet.
- `defect_log.md`, `final_test_report.md`, `requirements_traceability.md` and `manual_testing/manual_test_report.md` are **generated** by `scripts/build_reports.py` from these files and stop with an error if a cited test is missing or failed.

## 8. Environment limitations

SQLite only; Chrome only (headless); the login throttle is per process; concurrency is tested with a deterministic stale-object scenario, not parallel load; screenshots come from the demo data set.
