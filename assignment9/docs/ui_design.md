# UI Design Document — Assignment 9

**Project:** Hostel Management System (HMS) — Room Allocation Module  
**Assessment:** Assessment 9 — Design and Development of User Interface  
**Date:** 2026-10-20  
**Version:** 1.0

---

## 1. Purpose and Scope

This document describes the user interface design for the Room Allocation module of the Hostel Management System, built as Assignment 9 on top of the Assignment 8 backend implementation. The UI provides a polished, responsive, and accessible Bootstrap 5 interface for managing room allocations, viewing availability, and role-specific dashboards.

**Scope:** The UI covers the complete room allocation workflow — creating allocations, viewing and filtering allocation lists, reallocating students, cancelling allocations, viewing room availability, and role-specific dashboards for Admin, Warden, Student, and Accountant users.

---

## 2. Intended Users and Roles

| Role | Description | UI Access |
|------|-------------|-----------|
| **Admin** | System administrator with full access | All dashboards, allocation management, room management, student management, available rooms |
| **Warden** | Hostel warden managing room assignments | Warden dashboard, allocation management, room management, student management, available rooms |
| **Student** | Resident student | Student dashboard (personal profile + allocation), available rooms (read-only), personal allocation view |
| **Accountant** | Fee management (future) | Accountant dashboard (placeholder) |

---

## 3. UI Design Goals

1. **Consistency** — Unified design language across all pages using Bootstrap 5 components and custom CSS variables
2. **Visibility of System Status** — Clear feedback via flash messages, loading states, progress bars, and badges
3. **Error Prevention** — Inline validation, confirmation dialogs for destructive actions, required field indicators
4. **Feedback** — Success/error/warning toasts, form validation messages, real-time room availability preview
5. **Accessibility** — Semantic HTML, ARIA labels, focus indicators, keyboard navigation, sufficient contrast
6. **Responsive Design** — Mobile-first layout with collapsible sidebar, fluid grids, touch-friendly controls
6. **Credible HMS Look** — Professional color scheme, consistent spacing, card-based layout, meaningful icons

---

## 4. Page-by-Page Screen Descriptions

### 4.1 Login Page (`/auth/login`)
- **Layout:** Centered card with HMS branding
- **Fields:** Email (with autocomplete), Password (with show/hide toggle)
- **Demo Accounts:** Click-to-fill buttons for all four roles (configurable)
- **CSRF:** Protected form with hidden token
- **Accessibility:** Proper labels, autofocus on email, keyboard operable

### 4.2 Shared Layout (All Authenticated Pages)
- **Sidebar Navigation:** Fixed left sidebar (260px) with role-based menu items
  - Admin/Warden: Dashboard, Allocations, Available Rooms, Rooms, Students
  - Student: Dashboard, My Allocation, Available Rooms
- **Top Bar:** Page title, breadcrumb navigation, user info, logout
- **Main Content:** Fluid container with card-based layout
- **Footer:** System branding
- **Mobile:** Hamburger toggle, overlay backdrop, swipe-friendly

### 4.3 Admin Dashboard (`/`)
- **Summary Cards (4):** Total Students, Total Rooms, Occupied Rooms, Available Rooms
- **Bed Occupancy Progress Bar:** Visual percentage with count
- **Quick Actions Grid (5):** Allocate Room, View Allocations, Available Rooms, Manage Rooms, Manage Students
- **Recent Allocations Table:** Student, Room, Start Date, Status (max 5)

### 4.4 Warden Dashboard (`/`)
- **Summary Cards (4):** Total Rooms, Available Rooms, Occupied Rooms, Bed Occupancy %
- **Room Status Table:** Room, Block, Floor, Capacity, Occupancy (progress bar), Available beds, Status badge

### 4.5 Student Dashboard (`/`)
- **Profile Card:** Name, Email, Roll No, Course, Batch
- **Allocation Card:** Room, Block, Floor, Allocated Date, Start Date, End Date (if set), Status badge
- **Actions:** View Details link, View Available Rooms button (if no allocation)

### 4.6 Room Allocations List (`/allocation/`)
- **Header:** Title, count, "New Allocation" button
- **Search/Filter Bar:** Text search (student name, roll no, room, block), Block dropdown, Status dropdown
- **Data Table:** Student, Roll No, Room, Block, Allocated Date, Start Date, End Date, Status badge, Actions (Reallocate, Cancel)
- **Pagination:** Page numbers, Previous/Next, showing X to Y of Z
- **Empty State:** Friendly message when no allocations

### 4.7 Create Allocation (`/allocation/create`)
- **Form Fields:**
  - Student (dropdown, required)
  - Room (dropdown with capacity/availability info, required)
  - Start Date (date picker, required, min=today)
  - End Date (date picker, optional, min=start date)
- **Real-time Availability Preview:** Shows selected room capacity, occupancy, free beds, color-coded alert
- **Client-side Validation:** HTML5 required, min dates, custom JS for end date ≥ start date
- **Server-side Validation:** Duplicate allocation, room availability, date format, date range
- **Loading State:** Button disables with spinner on submit

### 4.8 Reallocate Room (`/allocation/<id>/reallocate`)
- **Split Layout:** Current allocation details (left) + New room selection (right)
- **Current Allocation:** Student info, current room, occupancy, dates
- **New Room Dropdown:** Excludes current room, shows availability
- **Availability Preview:** Same as create form
- **Validation:** Cannot select same room, must be available, CSRF protected

### 4.9 Available Rooms (`/allocation/available`)
- **Filter Bar:** Block dropdown, "Show full rooms" checkbox
- **Available Rooms Table:** Room, Block, Floor, Capacity, Occupancy (progress), Free beds (badge), Status
- **Full Rooms Table (optional):** Same columns, muted styling
- **Accessible to:** Admin, Warden, Student

### 4.10 Student Allocation View (`/allocation/student/<id>`)
- **Restricted:** Students only see their own (enforced server-side)
- **Room Details:** Room, Block, Floor, Capacity, Current Occupancy
- **Allocation Details:** Allocated date, Start date, End date, Status
- **Block Info:** Location, Block name

### 4.11 Room Management (`/rooms`) — Admin/Warden
- **Search:** Client-side filter input
- **Table:** Room, Block, Floor, Capacity, Occupancy, Available, Status

### 4.12 Student Management (`/students`) — Admin/Warden
- **Search:** Client-side filter input
- **Table:** Name, Email, Roll No, Course, Batch, Allocation (badge or "Not allocated")

---

## 5. Main Fields, Buttons, Actions, and Validation Messages

### Create Allocation Form
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Student | Select | Yes | Must exist, no active allocation |
| Room | Select | Yes | Must exist, has free beds, status=available |
| Start Date | Date | Yes | Valid ISO format, not required to be future |
| End Date | Date | No | Valid ISO format, ≥ start date if provided |

**Validation Messages:**
- "Student, room, and start date are required."
- "Selected student does not exist."
- "Selected room does not exist."
- "Student [name] already has an active room allocation."
- "Room [number] is not available (capacity: X, occupied: Y)."
- "Invalid date format. Use YYYY-MM-DD."
- "End date cannot be earlier than start date."
- "Allocation failed due to concurrent modification. Please try again."

### Reallocate Form
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| New Room | Select | Yes | Must exist, ≠ current room, has free beds, status=available |

**Validation Messages:**
- "New room is required."
- "Selected room does not exist."
- "Student is already in that room. Choose a different room."
- "Room [number] is not available."

### Cancel Action
- **Confirmation:** "Are you sure you want to cancel this allocation?" (via `data-confirm` attribute)
- **Success:** "Allocation cancelled successfully."
- **Failure:** "Cancellation failed."

---

## 6. Navigation Flow

```
Login
  │
  ├─→ Admin Dashboard
  │     ├─→ Allocations List
  │     │     ├─→ Create Allocation
  │     │     ├─→ Reallocate (per row)
  │     │     └─→ Cancel (per row)
  │     ├─→ Available Rooms
  │     ├─→ Rooms List
  │     └─→ Students List
  │
  ├─→ Warden Dashboard
  │     ├─→ Allocations List
  │     │     ├─→ Create Allocation
  │     │     ├─→ Reallocate
  │     │     └─→ Cancel
  │     ├─→ Available Rooms
  │     ├─→ Rooms List
  │     └─→ Students List
  │
  ├─→ Student Dashboard
  │     ├─→ My Allocation (personal view)
  │     └─→ Available Rooms
  │
  └─→ Accountant Dashboard (placeholder)
```

---

## 7. Design Principles Applied

| Principle | Implementation |
|-----------|----------------|
| **Consistency** | Shared base template, CSS variables, Bootstrap components, macro-based reusable UI elements |
| **Visibility of System Status** | Flash alerts (success/danger/warning/info), progress bars for occupancy, badges for status, loading spinners |
| **Error Prevention** | Required field markers, HTML5 validation, JS date logic, confirmation dialogs, server-side re-validation |
| **Feedback** | Toast-style alerts, inline form validation, real-time room availability preview, button loading states |
| **Accessibility** | Semantic HTML5, `label`+`for`, ARIA roles on progressbars, focus-visible outlines, sufficient contrast, keyboard navigation |
| **Responsive Design** | CSS Grid/Flexbox, breakpoint-based sidebar collapse, fluid tables with horizontal scroll, touch targets ≥44px |
| **User Control** | Clear back/cancel links, breadcrumb navigation, predictable form behavior |

---

## 8. UI Element to Functional Requirement Mapping

| UI Element | Functional Requirement (from Assignment 8) |
|------------|--------------------------------------------|
| Admin Dashboard stats | Room/bed occupancy tracking, allocation counts |
| Create Allocation form | FR-1: Allocate room to student with availability check |
| Duplicate student check | FR-2: Prevent duplicate active allocations |
| Room availability check | FR-3: Validate room capacity and status |
| Date range validation | FR-4: End date ≥ start date |
| Reallocate workflow | FR-5: Move student between rooms with occupancy update |
| Cancel workflow | FR-6: Cancel allocation, vacate bed, update status |
| Available rooms list | FR-7: View rooms with free beds |
| Student dashboard | FR-8: Student self-service view of own allocation |
| Role-based navigation | FR-9: Authorization per role (admin/warden/student) |
| CSRF tokens on all forms | FR-10: CSRF protection on state-changing operations |
| XSS-safe rendering | FR-11: Output escaping in templates |
| SQL injection resistance | FR-12: Parameterized queries via ORM |

---

## 9. Reuse of Assignment 8 Implementation

| Component | Reused From Assignment 8 | Changes Made |
|-----------|--------------------------|--------------|
| **Models** | `models.py` (User, Student, Room, RoomAllocation, HostelBlock, Warden, Admin, Accountant) | None — used as-is |
| **Auth** | `auth.py` (login_required, role_required, login_user, logout_user, get_current_user, CSRF) | None — used as-is |
| **Config** | `config.py` (Config, TestConfig) | Added APP_NAME, APP_SHORT_NAME |
| **Routes** | `auth_routes.py`, `main_routes.py`, `room_allocation_routes.py` | Enhanced with search, filter, pagination, better error handling |
| **Templates** | All templates | Complete rewrite with sidebar layout, enhanced components, accessibility |
| **CSS** | `hms.css` | Complete rewrite with design system, sidebar, responsive layout, dark mode |
| **Tests** | Test fixtures and patterns | New test files for UI rendering, navigation, accessibility, responsive layout |
| **Sample Data** | `init_sample_data()` | Preserved |

---

## 10. Intentionally Unimplemented Features

| Feature | Reason |
|---------|--------|
| **Warden Approval Workflow** | Assignment 8 sequence diagram shows approval step; backend auto-approves. UI would need new state (`pending_approval`) and warden approval UI — out of scope for this assessment. |
| **MySQL/PostgreSQL Concurrency** | SQLite used; true row-level locking (`SELECT FOR UPDATE`) and partial unique indexes require MySQL/PostgreSQL. Documented limitation in code comments. |
| **Past Start Date Restriction** | Allowed by design for admin backdating historical allocations. |
| **Fee/Complaint/Leave/Visitor UI** | Models exist as stubs; no routes implemented in Assignment 8. |
| **Email Notifications** | Not in Assignment 8 scope. |
| **Print-Optimized Styles** | Basic `@media print` included but not fully tested. |
| **Advanced DataTables** | Client-side search only; server-side pagination/filtering would require API endpoints. |

---

## 11. Technical Implementation Notes

### CSS Architecture
- **CSS Custom Properties** for theming (light/dark mode via `prefers-color-scheme`)
- **Component-based classes** (`.card`, `.stat`, `.dashboard-stat`, `.quick-action-btn`)
- **Utility classes** for spacing, colors, typography
- **Bootstrap 5 integration** — extends, doesn't override unnecessarily

### JavaScript
- **Minimal vanilla JS** — no framework dependency
- **Sidebar toggle** — mobile hamburger menu
- **Form validation** — HTML5 + custom `needs-validation` class
- **Date picker linking** — end date min = start date
- **Real-time availability preview** — reads data attributes from `<option>`
- **Auto-dismiss alerts** — 5-second timeout
- **Loading states** — button disable + spinner on submit
- **Tooltips** — Bootstrap tooltips on action buttons
- **Confirmation** — `data-confirm` attribute on destructive actions

### Accessibility
- **WCAG 2.1 AA** target: contrast ratios, focus indicators, keyboard operability
- **Semantic landmarks:** `<nav>`, `<main>`, `<header>`, `<footer>`, `<aside>`
- **ARIA:** `role="progressbar"` on occupancy bars, `aria-label` on icon-only buttons
- **Form associations:** Explicit `<label for="">` matching input `id`

---

## 12. Browser Support

- Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- No IE11 support (uses CSS custom properties, `focus-visible`, modern JS)

---

*End of UI Design Document*