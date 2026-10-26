# Manual test cases

*Generated from `manual_test_cases.csv`. Record results ONLY in `manual_test_execution.csv`.*

65 cases. Priority P1 = minimum set to execute; P2/P3 = recommended. Technique "UI + browser DevTools" means a developer tool (F12) is needed to tamper with a form.

## Authentication

### AUTH-01 - Valid admin login
*Requirement:* RA-11 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Server started with DEMO data (see TESTING_PROCEDURE.md section 3). Not logged in.

**Steps:**

    1. Open http://127.0.0.1:5000/auth/login
    2. Enter the admin e-mail and password
    3. Click Login

**Input data:** admin@hms.test / admin123

**Expected result:** Redirected to the Admin Dashboard; message "Welcome, Admin User!" is shown; sidebar shows the admin menu.

### AUTH-02 - Valid warden login
*Requirement:* RA-11 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Not logged in.

**Steps:**

    1. Open the login page
    2. Enter the warden e-mail and password
    3. Click Login

**Input data:** warden@hms.test / warden123

**Expected result:** Redirected to the Warden Dashboard; message "Welcome, Warden Smith!" is shown.

### AUTH-03 - Valid student login
*Requirement:* RA-11 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Not logged in.

**Steps:**

    1. Open the login page
    2. Enter the student e-mail and password
    3. Click Login

**Input data:** john@student.test / student123

**Expected result:** Redirected to the Student Dashboard; message "Welcome, John Doe!" is shown.

### AUTH-04 - Wrong password rejected
*Requirement:* RA-11 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Not logged in.

**Steps:**

    1. Open the login page
    2. Enter admin@hms.test with password "wrong-password"
    3. Click Login

**Input data:** admin@hms.test / wrong-password

**Expected result:** Stay on the login page; error "Invalid email or password." is shown; no session is created.

### AUTH-05 - Unknown user rejected
*Requirement:* RA-11 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Not logged in.

**Steps:**

    1. Open the login page
    2. Enter nobody@example.com with any password
    3. Click Login

**Input data:** nobody@example.com / x

**Expected result:** Same error "Invalid email or password." (the message must not reveal whether the account exists).

### AUTH-06 - Logout ends the session
*Requirement:* RA-11 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. Click Logout at the bottom of the sidebar
    2. In the address bar open http://127.0.0.1:5000/allocation/

**Input data:** -

**Expected result:** After step 1: login page with "You have been logged out."; after step 2: redirected to the login page with "Please log in to access this page."

### AUTH-07 - Anonymous access is blocked
*Requirement:* RA-11 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Not logged in.

**Steps:**

    1. Open http://127.0.0.1:5000/
    2. Open /allocation/
    3. Open /rooms

**Input data:** -

**Expected result:** Every URL redirects to the login page with "Please log in to access this page."

### AUTH-08 - Login requires a CSRF token
*Requirement:* RA-12 | *Priority:* P1 | *Technique:* UI + browser DevTools

**Preconditions:** Not logged in; browser DevTools open.

**Steps:**

    1. Open the login page
    2. In DevTools > Elements delete the hidden <input name="csrf_token">
    3. Enter valid admin credentials and click Login

**Input data:** admin@hms.test / admin123

**Expected result:** The server rejects the request: page titled "Your request could not be verified" (HTTP 400, visible in the DevTools Network tab). You are not logged in.

### AUTH-09 - Lockout after repeated failed logins
*Requirement:* RA-11 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Restart the server with LOGIN_MAX_ATTEMPTS=5 (TESTING_PROCEDURE.md section 3). Not logged in.

**Steps:**

    1. Submit the login form 5 times with dana@student.test and a wrong password
    2. Submit a 6th time with the CORRECT password (student123)
    3. Log in with john@student.test / student123

**Input data:** dana@student.test

**Expected result:** Attempts 1-5: "Invalid email or password."; attempt 6 (even with the correct password): "Too many failed login attempts. Try again in about 15 minute(s)."; step 3 (a different account) still works.

### AUTH-10 - Logout is not possible via a link (GET)
*Requirement:* RA-11, RA-12 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. In the address bar open http://127.0.0.1:5000/auth/logout
    2. Open http://127.0.0.1:5000/

**Input data:** -

**Expected result:** Step 1 shows "Method Not Allowed" (HTTP 405). Step 2 shows the dashboard: you are still logged in.

## Allocation

### ALLOC-01 - Allocate a student, open-ended
*Requirement:* RA-01 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin. Fresh demo data without allocations. No allocations exist.

**Steps:**

    1. Sidebar > Allocations > New Allocation
    2. Student: John Doe; Room: Block A, room 101
    3. Leave the start date at today; leave End date empty
    4. Click Create allocation

**Input data:** John Doe -> Block A / 101

**Expected result:** Redirected to the allocation list; message "Room 101 allocated to John Doe successfully."; list shows John Doe, Block A, room 101, Status Active, End "—".

### ALLOC-08 - Allocate with an end date
*Requirement:* RA-01 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** ALLOC-01 done.

**Steps:**

    1. New Allocation
    2. Student: Jane Smith; Room: Block A, room 101
    3. Start: today; End: today + 90 days
    4. Create allocation

**Input data:** Jane Smith -> Block A / 101

**Expected result:** Success message for room 101 and Jane Smith; list shows the end date. Room Block A 101 is now 2/2.

### ALLOC-05 - Student with an active allocation cannot get a second
*Requirement:* RA-03 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** ALLOC-01 done (John has an active allocation).

**Steps:**

    1. New Allocation
    2. Student: John Doe; Room: Block B, room 101
    3. Create allocation

**Input data:** John Doe -> Block B / 101

**Expected result:** Error "Student John Doe already has an active room allocation."; no new row in the allocation list.

### ALLOC-15 - Form keeps your input after a server-side error
*Requirement:* RA-02, UI-03 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Immediately after ALLOC-05.

**Steps:**

    1. Look at the New Allocation form that is displayed together with the error

**Input data:** -

**Expected result:** The form is shown again with Student = John Doe, Room = Block B 101 and the start date still selected (you do not have to re-enter everything).

### ALLOC-11 - Start date equal to end date is accepted
*Requirement:* RA-01 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. New Allocation
    2. Student: Bob Wilson; Room: Block A, room 102
    3. Start: today; End: today
    4. Create allocation

**Input data:** Bob Wilson -> Block A / 102

**Expected result:** Success message "Room 102 allocated to Bob Wilson successfully."

### ALLOC-02 - Allocating to a room that filled up meanwhile is refused
*Requirement:* RA-04 | *Priority:* P1 | *Technique:* UI + browser DevTools

**Preconditions:** Block A 102 has exactly 1 free bed (Bob only). Two browser tabs on the New Allocation form, both opened BEFORE step 1 (both list Block A 102).

**Steps:**

    1. Tab 1: allocate Alice Brown to Block A 102 and submit (succeeds, room now full)
    2. Tab 2 (stale form, still lists room 102): select Carlos Diaz and Block A 102, submit

**Input data:** Carlos Diaz -> Block A / 102 (stale form)

**Expected result:** Tab 2 shows error "Room 102 is not available (capacity: 2, occupied: 2)."; Carlos has no allocation; room 102 stays 2/2.

### ALLOC-09 - Warden can create an allocation
*Requirement:* RA-01 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as WARDEN (log out first).

**Steps:**

    1. New Allocation
    2. Student: Carlos Diaz; Room: Block A, room 201
    3. Create allocation

**Input data:** warden@hms.test / warden123 / Carlos Diaz -> Block A / 201

**Expected result:** Success message "Room 201 allocated to Carlos Diaz successfully."

### ALLOC-03 - Non-existent student id is rejected
*Requirement:* RA-02 | *Priority:* P2 | *Technique:* UI + browser DevTools

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open New Allocation
    2. In DevTools change the value of one <option> in the Student select to 99999
    3. Select that option, choose a room, submit

**Input data:** student_id=99999

**Expected result:** Error "Selected student does not exist."; nothing created.

### ALLOC-04 - Non-existent room id is rejected
*Requirement:* RA-02 | *Priority:* P2 | *Technique:* UI + browser DevTools

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open New Allocation
    2. In DevTools change the value of one <option> in the Room select to 99999
    3. Select a student and that room option, submit

**Input data:** room_id=99999

**Expected result:** Error "Selected room does not exist."; nothing created.

### ALLOC-06 - Required fields
*Requirement:* RA-02 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open New Allocation
    2. Leave Student and Room unselected
    3. Click Create allocation

**Input data:** -

**Expected result:** The form is not submitted: the empty required fields are highlighted/flagged and the Create allocation button is still clickable (it must not stay stuck on "Processing..."). (If you bypass the browser check the server answers "Student, room, and start date are required.")

### ALLOC-07 - Invalid date text is rejected
*Requirement:* RA-02 | *Priority:* P2 | *Technique:* UI + browser DevTools

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open New Allocation
    2. In DevTools change the Start date <input type="date"> to type="text"
    3. Type 2026-13-45; select student and room; submit

**Input data:** 2026-13-45

**Expected result:** Error "Invalid date format. Use YYYY-MM-DD."; nothing created; entered values kept.

### ALLOC-10 - End date before start date is rejected
*Requirement:* RA-02 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open New Allocation
    2. Choose a student without allocation (Dana Evans) and any available room
    3. Start: today + 10 days; End: today + 5 days
    4. Submit

**Input data:** start > end

**Expected result:** Submission refused: either the browser/JS shows a validation message ("End date cannot be earlier than start date.") or the server shows it; the button stays clickable; no allocation created.

### ALLOC-14 - Dates outside 2000-2100 are rejected
*Requirement:* RA-02 | *Priority:* P2 | *Technique:* UI + browser DevTools

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open New Allocation
    2. In DevTools change Start date to type="text" and enter 1900-01-01; choose Dana Evans and a room; submit
    3. Repeat with 9999-12-31

**Input data:** 1900-01-01 / 9999-12-31

**Expected result:** Error "Dates must be between 2000-01-01 and 2100-12-31." both times; nothing created.

### ALLOC-13 - Create requires a CSRF token
*Requirement:* RA-12 | *Priority:* P1 | *Technique:* UI + browser DevTools

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open New Allocation and fill it with valid data (Dana Evans, Block A 202)
    2. In DevTools delete the hidden <input name="csrf_token">
    3. Submit

**Input data:** -

**Expected result:** Page "Your request could not be verified" (HTTP 400); no allocation created for Dana Evans.

## Occupancy

### OCC-01 - Room becomes Full at capacity
*Requirement:* RA-04 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** ALLOC-01 and ALLOC-08 done.

**Steps:**

    1. Sidebar > Rooms
    2. Find Block A room 101

**Input data:** -

**Expected result:** Block A 101 shows 2 of 2 beds occupied and status Full.

### OCC-02 - Room becomes Available again when a bed is freed
*Requirement:* RA-04 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Right after REALLOC-01.

**Steps:**

    1. Sidebar > Rooms
    2. Find Block A room 101

**Input data:** -

**Expected result:** Block A 101 shows 1 of 2 beds occupied and status Available.

### OCC-03 - Full rooms cannot be picked when creating
*Requirement:* RA-04 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Block A 102 is full.

**Steps:**

    1. New Allocation > open the Room drop-down

**Input data:** -

**Expected result:** Block A 102 is not offered.

## Reallocation

### REALLOC-01 - Reallocate to a room with a free bed
*Requirement:* RA-05 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** John has an active allocation in Block A 101 (full 2/2).

**Steps:**

    1. Allocations list > click the Reallocate icon on John Doe
    2. New room: Block B, room 101
    3. Click Reallocate

**Input data:** John: A/101 -> B/101

**Expected result:** Message "Student reallocated to room 101 successfully."; list shows John in Block B. Rooms page: Block A 101 is now 1/2 and Available; Block B 101 is 1/3.

### REALLOC-03 - Full rooms are not offered
*Requirement:* RA-05, RA-04 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Block A 102 is full (Bob + Alice from ALLOC-02).

**Steps:**

    1. Click Reallocate on Carlos Diaz
    2. Open the "New room" drop-down

**Input data:** -

**Expected result:** Block A 102 (full) is not in the list; only rooms with a free bed are offered.

### REALLOC-06 - Reallocating to the same room is refused
*Requirement:* RA-05 | *Priority:* P3 | *Technique:* UI + browser DevTools

**Preconditions:** Jane Smith is allocated to Block A 101 (room id 1 in the demo data).

**Steps:**

    1. Click Reallocate on Jane Smith (her current room is not offered in the list)
    2. In DevTools > Elements change the value of any one <option> in the "New room" select to 1 (the id of Block A 101)
    3. Select that option and click Reallocate

**Input data:** new_room_id=1 (her current room)

**Expected result:** Error "Student is already in that room. Choose a different room."; no change to the allocation or room counters.

### REALLOC-04 - Room is required
*Requirement:* RA-05 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Reallocate form open.

**Steps:**

    1. Leave "Select new room" selected
    2. Click Reallocate

**Input data:** -

**Expected result:** Not submitted (field flagged) and the Reallocate button stays clickable; if bypassed the server says "New room is required."

### REALLOC-02 - Non-existent room id is rejected
*Requirement:* RA-05 | *Priority:* P3 | *Technique:* UI + browser DevTools

**Preconditions:** Reallocate form open.

**Steps:**

    1. In DevTools change an <option> value to 99999
    2. Select it and click Reallocate

**Input data:** room_id=99999

**Expected result:** Error "Selected room does not exist."; allocation unchanged.

### REALLOC-05 - Reallocate requires a CSRF token
*Requirement:* RA-12 | *Priority:* P1 | *Technique:* UI + browser DevTools

**Preconditions:** Reallocate form open.

**Steps:**

    1. Delete the hidden csrf_token input in DevTools
    2. Choose a room; click Reallocate

**Input data:** -

**Expected result:** Page "Your request could not be verified" (HTTP 400); allocation unchanged.

## Cancellation

### CANCEL-02 - "Go back" keeps the allocation
*Requirement:* RA-06, UI-03 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Active allocation exists (Carlos Diaz, Block A 201).

**Steps:**

    1. Allocations list > click the red Cancel (x) icon on Carlos Diaz
    2. In the dialog click "Go back"

**Input data:** -

**Expected result:** A modal "Please confirm - Are you sure you want to cancel this allocation?" appears; after Go back the dialog closes and the allocation is still Active.

### CANCEL-01 - Confirm cancels and frees the bed
*Requirement:* RA-06 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** As CANCEL-02.

**Steps:**

    1. Click the Cancel (x) icon on Carlos Diaz again
    2. Click "Confirm"

**Input data:** -

**Expected result:** Message "Allocation cancelled successfully."; Carlos no longer appears under Status = Active; Block A 201 shows 0 of 2 beds.

### CANCEL-04 - Cancelled allocations offer no actions
*Requirement:* RA-06 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** CANCEL-01 done.

**Steps:**

    1. Allocations list > set Status filter to Cancelled > Filter

**Input data:** -

**Expected result:** Carlos Diaz is listed with status Cancelled and there are no Reallocate/Cancel buttons on that row.

### CANCEL-03 - Cancel requires a CSRF token
*Requirement:* RA-12 | *Priority:* P1 | *Technique:* UI + browser DevTools

**Preconditions:** Active allocation exists (e.g. Bob Wilson).

**Steps:**

    1. In DevTools delete the hidden csrf_token input inside the Cancel form of Bob Wilson
    2. Click Cancel and Confirm

**Input data:** -

**Expected result:** Page "Your request could not be verified" (HTTP 400); Bob's allocation is still Active.

## Allocation list

### LIST-01 - Search filters the list
*Requirement:* RA-07 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Several active allocations.

**Steps:**

    1. Allocations list > type "Jane" in the search box > Filter
    2. Search "nobody-matches"

**Input data:** Jane / nobody-matches

**Expected result:** Step 1: only Jane Smith's row; step 2: "No allocations found."

### LIST-02 - Block and status filters
*Requirement:* RA-07 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Active and cancelled allocations exist.

**Steps:**

    1. Select Block B > Filter
    2. Select Status Cancelled > Filter

**Input data:** -

**Expected result:** Step 1 lists only Block B rows; step 2 lists only cancelled allocations.

## Available rooms

### AVAIL-01 - Only rooms with free beds are listed
*Requirement:* RA-08 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Block A 101 (1/2), Block A 102 (full).

**Steps:**

    1. Sidebar > Available Rooms

**Input data:** -

**Expected result:** Block A 102 (full) is NOT listed; Block A 101 is listed with its free beds.

### AVAIL-03 - Block filter and "Show full rooms"
*Requirement:* RA-08, RA-04 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** As AVAIL-01.

**Steps:**

    1. Tick "Show full rooms"
    2. Choose Block B in the block drop-down

**Input data:** -

**Expected result:** Step 1: Block A 102 appears marked full. Step 2: only Block B rooms are shown (no Block A rooms, full or not).

### AVAIL-02 - Student can view available rooms (read-only)
*Requirement:* RA-08 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as student.

**Steps:**

    1. Sidebar > Available Rooms

**Input data:** -

**Expected result:** Page loads; no allocation actions are offered.

## Student view

### STUDENT-01 - Student sees own allocation
*Requirement:* RA-09 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as John Doe (allocated).

**Steps:**

    1. Sidebar > My Allocation

**Input data:** -

**Expected result:** Page shows John Doe's room and block (Block B 101 after REALLOC-01).

### STUDENT-02 - Student cannot view another student's allocation
*Requirement:* RA-09 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as John Doe. Jane Smith has student id 2.

**Steps:**

    1. In the address bar open http://127.0.0.1:5000/allocation/student/2

**Input data:** -

**Expected result:** Redirected to the dashboard with "You can only view your own allocation."

## Authorization

### AUTHZ-01 - Admin reaches all management pages
*Requirement:* RA-10 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open Allocations, New Allocation, Available Rooms, Rooms, Students from the sidebar/buttons

**Input data:** -

**Expected result:** All pages load without a permission error.

### AUTHZ-02 - Warden reaches all management pages
*Requirement:* RA-10 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as warden.

**Steps:**

    1. Repeat the AUTHZ-01 pages

**Input data:** -

**Expected result:** All pages load.

### AUTHZ-03 - Student blocked from allocation management
*Requirement:* RA-10 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as student.

**Steps:**

    1. Open http://127.0.0.1:5000/allocation/
    2. Open /allocation/create

**Input data:** -

**Expected result:** Each redirects to the dashboard with "You do not have permission to access this page."

### AUTHZ-05 - Accountant blocked from allocations
*Requirement:* RA-10 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as accountant@hms.test / accountant123.

**Steps:**

    1. Open /allocation/

**Input data:** -

**Expected result:** Redirected with "You do not have permission to access this page."

### AUTHZ-07 - Student blocked from rooms and students pages
*Requirement:* RA-10 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as student.

**Steps:**

    1. Open /rooms
    2. Open /students

**Input data:** -

**Expected result:** Both redirect with "You do not have permission to access this page."

### AUTHZ-10 - Student cannot open another allocation's reallocate page
*Requirement:* RA-10 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as student. An allocation with id 2 exists.

**Steps:**

    1. Open http://127.0.0.1:5000/allocation/2/reallocate

**Input data:** -

**Expected result:** Redirected with "You do not have permission to access this page."

### AUTHZ-11 - Student cannot cancel an allocation
*Requirement:* RA-10, RA-12 | *Priority:* P2 | *Technique:* UI + browser DevTools

**Preconditions:** Logged in as student. Allocation id 2 is Active.

**Steps:**

    1. Open DevTools > Console and run:
    fetch("/allocation/2/cancel",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"csrf_token="+document.querySelector("input[name=csrf_token]").value})
    2. Log in as admin and check allocation 2

**Input data:** -

**Expected result:** The student request is refused (redirect to the dashboard / permission message); allocation 2 is still Active.

## Security

### SEC-01 - SQL injection in the search box
*Requirement:* RA-14 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. Allocations list > search for: ' OR '1'='1
    2. Search for: '; DROP TABLE rooms; --

**Input data:** SQL payloads

**Expected result:** Page renders normally ("No allocations found." or a normal list); no error page; Rooms page still shows all rooms.

### SEC-03 - XSS in the search box
*Requirement:* RA-14 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. Allocations list > search for: <script>alert(1)</script>

**Input data:** <script>alert(1)</script>

**Expected result:** No alert box appears; the text is displayed as plain text in the search field (escaped).

### SEC-05 - Forged CSRF token is rejected
*Requirement:* RA-12 | *Priority:* P2 | *Technique:* UI + browser DevTools

**Preconditions:** Logged in as admin.

**Steps:**

    1. Open New Allocation, fill the form
    2. In DevTools set the hidden csrf_token value to "forged"
    3. Submit

**Input data:** csrf_token=forged

**Expected result:** Page "Your request could not be verified" (HTTP 400); nothing created.

### SEC-06 - No session bleed between users
*Requirement:* RA-11 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** -

**Steps:**

    1. Log in as admin, then Logout
    2. Log in as warden

**Input data:** -

**Expected result:** Warden Dashboard shows the warden's name and no admin-only content.

### SEC-07 - Demo credentials are not displayed
*Requirement:* RA-13 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Server started normally (SHOW_DEMO_CREDENTIALS not set).

**Steps:**

    1. Open the login page and read it completely

**Input data:** -

**Expected result:** No demo accounts or passwords are listed on the page.

## Dashboards

### DASH-01 - Dashboards match the data
*Requirement:* RA-15 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Allocations from the cases above exist.

**Steps:**

    1. View the Admin, Warden and Student dashboards in turn

**Input data:** -

**Expected result:** Admin: Total Students = 6 and Total Rooms = 6 equal what the Students and Rooms pages show; active allocations and occupancy bar agree with the Allocations list. Student: shows own room.

## UI

### UI-01 - Mobile layout (390 px wide)
*Requirement:* UI-02 | *Priority:* P1 | *Technique:* UI + browser DevTools

**Preconditions:** Logged in as admin; DevTools device toolbar set to 390 x 844.

**Steps:**

    1. Visit Dashboard, Allocations, Available Rooms, Rooms, Students, New Allocation
    2. On each page: scroll horizontally; look at the title next to the hamburger button
    3. Tap the hamburger button

**Input data:** -

**Expected result:** No page scrolls sideways (wide tables scroll inside their card); the hamburger never covers the page title; tapping it opens the navigation drawer.

### UI-02 - Menus match the role
*Requirement:* UI-01 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** -

**Steps:**

    1. Log in as admin, then warden, then student; read the sidebar each time

**Input data:** -

**Expected result:** Admin and warden: Dashboard, Allocations, Available Rooms, Rooms, Students. Student: Dashboard, Available Rooms, My Allocation. "My Allocation" never appears for admin/warden.

### UI-03 - Single logout; cache not reused after logout
*Requirement:* UI-05, RA-11 | *Priority:* P1 | *Technique:* UI only

**Preconditions:** Logged in as admin.

**Steps:**

    1. Count the Logout controls visible on screen
    2. Click Logout
    3. Press the browser Back button

**Input data:** -

**Expected result:** Exactly one Logout control. After Back the dashboard content is NOT shown; you are sent to the login page.

## Data entry

### ADD-01 - Add a hostel block
*Requirement:* RA-16 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as admin. Run AFTER all other cases (it changes the totals checked by DASH-01).

**Steps:**

    1. Sidebar > Rooms > Add block
    2. Block name: Block C; Location: South Campus
    3. Click Add block

**Input data:** Block C / South Campus

**Expected result:** Redirected to the Rooms page with the message "Block "Block C" added."; Block C appears in the block filter of Allocations.

### ADD-02 - Add a room
*Requirement:* RA-16 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** ADD-01 done.

**Steps:**

    1. Rooms > Add room
    2. Block: Block C; Room number: 301; Floor: 3; Capacity: 2; Status: Available
    3. Click Add room

**Input data:** Block C / 301 / floor 3 / 2 beds

**Expected result:** Message "Room 301 added to Block C."; the Rooms table shows Block C 301 with 0 / 2 beds" and status Available; the New Allocation room list offers it."

### ADD-03 - Add a student and log in as that student
*Requirement:* RA-16 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** ADD-02 done.

**Steps:**

    1. Students > Add student
    2. Name: Frank Green; E-mail: frank@student.test; Roll number: STU900; Course: B.Tech IT; Batch: 2026; Password and confirmation: Frank#Pass123
    3. Click Add student
    4. Log out; log in as frank@student.test / Frank#Pass123

**Input data:** Frank Green / STU900

**Expected result:** Message "Student Frank Green (STU900) added."; Frank appears in the Students list with no allocation; the new login works and shows the student menu (Dashboard, Available Rooms, My Allocation).

### ADD-04 - Validation and duplicates on the add forms
*Requirement:* RA-16 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as admin; ADD-03 done.

**Steps:**

    1. Add student with E-mail john@student.test and everything else valid
    2. Add student with Roll number STU900 and a new e-mail
    3. Add student with Password abc and confirmation abc
    4. Add room: Block C, room number 301 again
    5. Add block named "block c"

**Input data:** see steps

**Expected result:** 1: "A user with e-mail john@student.test already exists."; 2: "Roll number STU900 is already in use."; 3: "Password must be 8 to 128 characters long."; 4: "Room 301 already exists in Block C."; 5: "A block named "block c" already exists." Every form is shown again with your entries kept (passwords are never refilled); nothing is created.

### ADD-05 - Only admins can add data
*Requirement:* RA-16, RA-10 | *Priority:* P2 | *Technique:* UI only

**Preconditions:** Logged in as warden, then as student.

**Steps:**

    1. As warden open Rooms and Students: look for Add buttons
    2. As warden open http://127.0.0.1:5000/rooms/new
    3. As student open http://127.0.0.1:5000/students/new

**Input data:** -

**Expected result:** Warden sees no Add buttons; both URLs redirect to the dashboard with "You do not have permission to access this page."
