# Initial Review — HMS Repository Assessment 8

**Date:** 2026-10-19  
**Assessor:** Kilo AI  
**Repository Root:** `/home/roxxon/Desktop/VIT Studies/FALL SEM 2026-27/Software Engineering/Lab`

---

## 1. Repository Structure Analysis

The repository contains **only documentation and UML diagrams** — **no executable Flask application source code** exists.

### Directory Layout
```
/home/roxxon/Desktop/VIT Studies/FALL SEM 2026-27/Software Engineering/Lab/
├── ver1/                    # DFDs, ERDs, Flowcharts (StarUML .mdj + PNG exports)
├── ver2/                    # Class Diagram, Use Case Diagram, Sequence Diagrams (Room Allocation)
├── ver3/                    # Collaboration, Deployment, Component, Package Diagrams
├── *.mdj files              # StarUML project files
├── *.png / *.jpg files      # Diagram exports
├── *.pdf files              # Assignment submissions (1-6)
├── Hostel_Management_System_Assignment.md   # Project specification (Tasks 1-3)
├── Hostel_Management_System_Summary.md      # Handwritten summary
└── build_hostel_erd_staruml.js              # ERD generation script
```

### Key Documentation Files
| File | Purpose |
|------|---------|
| `Hostel_Management_System_Assignment.md` | Full project spec: requirements, stack, WBS, methodology |
| `Hostel_Management_System_Summary.md` | Handwritten Q1-Q3 summary |
| `ver2/HMS_Class_Diagram.mdj` | Complete class model (User, Admin, Warden, Student, Accountant, Room, RoomAllocation, Complaint, LeaveRequest, Fee, Notice, Report, Visitor) |
| `ver2/HMS_Sequence_Diagram_RoomAllocation.mdj` | Room Allocation sequence: Student → Web Interface → Controller → Room → DB → Warden |
| `ver2/HMS_Use_Case_Diagram.mdj` | Use cases for all 4 roles |

---

## 2. Technology Stack (from Documentation)

| Layer | Technology |
|-------|------------|
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Backend | Python, Flask |
| Database | MySQL 8.x |
| IDE | VS Code |
| Version Control | Git & GitHub |
| Testing | Manual Testing (per assignment) |
| Deployment | Localhost only |

---

## 3. Module Analysis for Testing

From the WBS and Class Diagram, the **Room Allocation** module is the best candidate because:

1. **Well-defined sequence diagram** exists (`ver2/HMS_Sequence_Diagram_RoomAllocation.mdj`)
2. **Clear class model** with `Room`, `RoomAllocation`, `Student`, `Warden` entities
3. **Explicit workflow**: request → check availability → allocate → notify warden → confirm/reject
4. **Testable business rules**:
   - Room capacity vs. occupied beds
   - Availability status tracking
   - Duplicate allocation prevention
   - Warden approval/rejection
   - Reallocation and cancellation

### Room Allocation Key Classes (from Class Diagram)
- **Room**: roomId, roomNumber, floor, capacity, occupiedBeds, status | checkAvailability(), allocateStudent(), vacateStudent()
- **RoomAllocation**: allocationId, allocationDate, startDate, endDate | allocate(), reallocate(), cancel()
- **Student**: studentId, rollNo, course, batch | register(), viewProfile(), requestLeave(), submitComplaint(), viewFees()
- **Warden**: wardenId, department | approveLeave(), updateComplaint(), manageRoom()

---

## 4. Application Executability

**No Flask application exists.** The repository is documentation-only. To fulfill Assessment 8, a **minimal working Flask implementation** of the Room Allocation module must be created alongside the testing system.

---

## 5. Selected Module for Assessment 8

**Room Allocation** — Selected based on:
- Complete sequence diagram available
- Clear class definitions with operations
- Well-defined business logic (availability, capacity, warden approval)
- Central to HMS functionality

---

## 6. Testing Approach

Since no application exists, the assessment will:
1. **Build a minimal Flask HMS** with Room Allocation module matching the documented design
2. **Use SQLite for testing** (isolated, no MySQL dependency) — documented as adaptation
3. **Implement pytest suite** with fixtures for app, DB, auth, test data
4. **Execute real tests** against the implementation
5. **Document manual test procedures** for human verification
6. **Produce honest reports** reflecting actual test results

---

## 7. Gaps Identified

| Gap | Impact | Mitigation |
|-----|--------|------------|
| No Flask source code | Cannot test existing implementation | Build minimal implementation per spec |
| No database schema SQL | Cannot verify MySQL-specific behavior | Create SQLAlchemy models from class diagram; note SQLite adaptation |
| No authentication implementation | Cannot test RBAC | Implement basic session-based auth per User class |
| No requirements.txt | Unknown dependencies | Define minimal dependencies for test environment |

---

## 8. Next Steps

1. Create `requirements-test.txt` with test dependencies
2. Implement minimal Flask app (`app.py`) with Room Allocation routes
3. Create SQLAlchemy models matching class diagram
4. Build pytest fixtures and test cases
5. Create manual testing documentation
6. Execute tests and generate reports