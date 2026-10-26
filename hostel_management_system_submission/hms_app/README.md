# hms_app - Hostel Management System (Room Allocation module)

One Flask application shared by Assessment 8 (testing) and Assessment 9 (user interface).

```
hms_app/
├── __init__.py        app factory: CSRF, security headers (CSP nonce), login throttle, CLI commands
├── config.py          Config / TestConfig (environment driven, no hard-coded secrets)
├── models.py          SQLAlchemy models; atomic bed counters; CHECK constraints; partial unique index
├── auth.py            session helpers, role decorators, LoginThrottle, safe-redirect check
├── seed.py            opt-in demo data and create-admin helper (never runs automatically)
├── routes/            auth_routes, main_routes (dashboards, rooms, students), room_allocation_routes, admin_data_routes (add block/room/student)
├── templates/         Jinja templates (layouts, pages, _flashes.html, csrf_error.html)
└── static/            css/hms.css and vendor/ (Bootstrap 5.3.3, Bootstrap Icons 1.11.3 - self-hosted)
```
