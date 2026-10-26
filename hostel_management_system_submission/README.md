# Hostel Management System - Room Allocation module

One Flask application, one test suite and one dependency set serving **Assessment 8 (testing)** and **Assessment 9 (user interface)** of BCSE301P Software Engineering.

```
.
├── hms_app/                  the application (shared by both assessments)
├── tests/                    the single automated test suite (pytest)
├── docs/requirements.csv     shared requirement IDs (RA-xx module, UI-xx interface)
├── scripts/                  run_tests.py, build_reports.py, serve_demo.py, run_browser_checks.sh, browser/ (puppeteer tools)
├── requirements.txt          runtime dependencies          requirements-test.txt  + test tooling
├── run.py                    starts the app
├── assessment8_testing/      Assessment 8 deliverables: docs/TESTING_PROCEDURE.md, manual_testing/, results/, defect_log.md, final_test_report.md, requirements_traceability.md
└── assessment9_ui/           Assessment 9 deliverables: docs/ui_design.md, docs/requirement_traceability.md, docs/browser_verification.txt, screenshots/
```

## Run it

Run each line separately, from the project folder:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
flask --app run create-admin
python run.py
```
(Windows: `venv\Scripts\activate` instead of `source ...`, and `set SECRET_KEY=any-long-random-text`.)

- `pip install` must be run **inside the activated venv**; otherwise `python run.py` fails with `No module named ...`.
- `SECRET_KEY` is optional but keeps logins valid across restarts; without it a random key is used each start.
- `create-admin` asks for name, e-mail and password. Then open http://127.0.0.1:5000.
- No accounts exist and no demo passwords are shown by default.
- A new installation is empty. Log in as the admin, then use **Rooms > Add block**, **Rooms > Add room** and **Students > Add student** to enter data. To try the app with sample data instead, use the demo server below.

**Demo / manual testing** (throw-away database, well-known demo passwords - local use only):
```
python scripts/serve_demo.py            # see assessment8_testing/docs/TESTING_PROCEDURE.md for accounts and variants
```

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `SECRET_KEY` | random per process (warning logged) | signs sessions; set it for stable sessions |
| `DATABASE_URL` | `sqlite:///hms.db` (in `instance/`) | database |
| `FLASK_DEBUG` | off | `1` enables the interactive debugger (local development only) |
| `SESSION_COOKIE_SECURE` | `0` | set `1` under HTTPS (also sends HSTS) |
| `HMS_SEED_DEMO_DATA` | `0` | `1` loads demo users/rooms at start (never on a real deployment) |
| `SHOW_DEMO_CREDENTIALS` | `0` | `1` lists demo accounts on the login page |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_SECONDS` | `5` / `900` | login throttling |

Databases created before this revision lack the new CHECK constraints and partial unique index; recreate them (there is no migration tooling).

## Test it

```
pip install -r requirements-test.txt
python scripts/run_tests.py             # tests + coverage + JUnit + all generated reports
scripts/run_browser_checks.sh           # optional: headless-Chrome checks + screenshots (needs Node.js)
scripts/run_manual_doc.sh               # optional: refresh the manual test document and its reference screenshots
```

## Status and honest limits

- Automated tests, coverage and browser checks: see `assessment8_testing/final_test_report.md` (generated from the artifacts in `assessment8_testing/results/`).
- **Manual testing has not been executed.** `assessment8_testing/manual_testing/manual_test_execution.csv` lists every case as *Not Executed*; follow `assessment8_testing/docs/TESTING_PROCEDURE.md` section 4, then run `python scripts/build_reports.py`.
- Open defects and limitations: `assessment8_testing/defect_log.md`.
