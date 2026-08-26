# Walkthrough — Phase 5: Scheduling Agent

**Date Completed:** 2026-08-24  
**Phase:** 5 — First Vertical Slice: Scheduling Agent  
**Baseline:** Phase 1–4 complete, 24/24 tests passing  
**Final Verified State:** 29/29 pytest tests passing, 58/58 E2E checks passing

---

## Phase 5 Objective

Phase 5 implements the Scheduling Agent as a complete vertical slice on top of the Phase 1–4 foundation. The goal was to allow a patient to:

1. State a scheduling intent through the existing chat interface.
2. Receive a specific mock appointment slot with doctor, specialty, and time details.
3. Approve or reject the booking through the Phase 3 HITL workflow.
4. Have the backend create a verified appointment record in PostgreSQL on approval.
5. View their appointments through a new `📅 My Appointments` UI.
6. Cancel an appointment through the UI, with status persisted to the database.

**Strict constraints preserved from prior phases:**
- The deterministic red-flag safety engine (Phase 4) continues to intercept emergency symptoms before any scheduling logic runs.
- No appointment booking may occur without explicit patient approval through the HITL workflow.
- The scheduling provider is synthetic/mock and explicitly declared as such.
- HealthSync AI remains a care-coordination assistant, not a clinical decision system.

---

## Architecture & Components Added

### New Files

| File | Purpose |
|---|---|
| [`app/services/scheduling.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/services/scheduling.py) | Synthetic scheduling service: `search_available_slots()`, `book_appointment_slot()` |
| [`tests/test_scheduling.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_scheduling.py) | Phase 5 automated test suite (5 tests) |

### Modified Files

| File | Change |
|---|---|
| [`app/models.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/models.py) | Added `Appointment` SQLAlchemy model |
| [`app/crud.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/crud.py) | Added `create_appointment()`, `get_patient_appointments()`, `cancel_appointment()` |
| [`app/services/graph.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/services/graph.py) | Replaced Phase 3 scheduling stub with full `scheduling_node` |
| [`app/main.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/main.py) | Added `GET /appointments/me`, `POST /appointments/{id}/cancel`; forwarded `selected_slot` in `/chat` response |
| [`app/schemas_ai.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/schemas_ai.py) | Added `AppointmentResponse` schema; added `selected_slot` field to `ChatResponse`; added `created_at: Optional[datetime]` (Milestone 5 fix) |
| [`app/services/triage.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/services/triage.py) | Added `"heart attack"`, `"cardiac arrest"`, `"stopped breathing"`, `"not breathing"` to `RED_FLAG_PATTERNS` (Milestone 5 fix) |
| [`streamlit_app.py`](file:///d:/AI%20Agents/healthsync-ai-agent/streamlit_app.py) | Added `📅 My Appointments` nav item; upgraded HITL card to show slot details; added My Appointments panel with listing and cancel buttons; stored `selected_slot` in chat history |

---

## Appointment Data Model

The `Appointment` table was added to `app/models.py`:

```python
class Appointment(Base):
    __tablename__ = "appointments"

    id              = Column(Integer, primary_key=True)
    patient_id      = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_name     = Column(String, nullable=False)
    specialty       = Column(String, nullable=False)
    appointment_time= Column(String, nullable=False)
    status          = Column(String, default="scheduled")   # "scheduled" | "cancelled"
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="appointments")
```

CRUD operations in `app/crud.py`:
- `create_appointment(db, patient_id, doctor_name, specialty, appointment_time, notes)` → inserts and refreshes
- `get_patient_appointments(db, patient_id)` → patient-scoped list query
- `cancel_appointment(db, patient_id, appointment_id)` → sets `status = "cancelled"` only for matching patient

---

## Synthetic Scheduling Service

`app/services/scheduling.py` provides:

### `search_available_slots(specialty, date_preference) → List[dict]`

Returns a deterministic list of mock slots keyed by specialty. Each slot contains:

```json
{
  "slot_id": "slot_01",
  "doctor_name": "Dr. Alex Smith (Dermatologist)",
  "specialty": "Dermatologist",
  "appointment_time": "tomorrow at 10:00 AM",
  "is_mock": true,
  "source_name": "Mock Demo Availability Provider"
}
```

> ⚠️ This is not real availability. No real doctor, hospital, or calendar service is queried.

### `book_appointment_slot(db, patient_id, slot, session_id) → dict`

On approval:
1. Calls `crud.create_appointment()`.
2. Immediately re-queries the database to verify the row was persisted.
3. Returns a confirmation dict with `appointment_id` and slot details.
4. Raises an exception if DB verification fails — the confirmation message is never sent without a verified DB record.

---

## LangGraph Scheduling Agent Flow

The `scheduling_node` in `app/services/graph.py` replaced the Phase 3 placeholder stub.

### Execution flow on a scheduling request:

```
scheduling_node called
    ↓
Extract entities (specialty, date_preference) from state
    ↓
search_available_slots(specialty, date_preference)
    ↓
Select first available slot
    ↓
interrupt({
    "message": "Here is an available slot for your approval...",
    "selected_slot": { doctor_name, specialty, appointment_time, is_mock }
})
    ↓
[Graph paused — patient sees HITL card in Streamlit]
    ↓
POST /chat/approve → Command(resume="approved"/"rejected")
    ↓
scheduling_node resumes
    ↓
If "rejected":
    → set approval_status = "rejected"
    → return "No appointment was created" response
    → 0 DB mutations

If "approved":
    → book_appointment_slot(db, patient_id, slot)
    → DB re-query verification
    → set final_response = "✅ Appointment confirmed! Appointment ID: ..."
    → set approval_status = "approved"
```

### Safety Precedence

The `input_screening_node` runs **before** the Supervisor and `scheduling_node`. If the input contains any `RED_FLAG_PATTERNS` term (including `"heart attack"`, `"chest pain"`, etc.), execution branches immediately to emergency escalation and **never reaches the Scheduling Agent**. This cannot be overridden by LLM output or prompt injection.

---

## HITL Approval / Rejection Flow

Phase 3's `interrupt()` / `Command(resume=...)` mechanism is reused unchanged.

| Step | Mechanism |
|---|---|
| Graph pauses | `interrupt()` in `scheduling_node` |
| State preserved | `MemorySaver` checkpointer |
| Approval/rejection | `POST /chat/approve` → `Command(resume={"decision": "approved"/"rejected"})` |
| Graph resumes | `scheduling_node` continues from the interrupt point |

**On Rejection:** Zero DB mutations. The scheduling node detects `"rejected"` and returns without calling `book_appointment_slot()`.

**On Approval:** `book_appointment_slot()` is called, DB insertion is verified, confirmation is returned.

---

## Appointment API Endpoints

### `GET /appointments/me`

- Requires: `Authorization: Bearer <patient_token>`
- Returns: `List[AppointmentResponse]` — only appointments belonging to the authenticated patient.
- Admin role: blocked (403).

### `POST /appointments/{appointment_id}/cancel`

- Requires: `Authorization: Bearer <patient_token>`
- Returns: `AppointmentResponse` with `status = "cancelled"`.
- Other patients' appointments: 404 (no cross-patient mutation possible).
- Non-existent appointment ID: 404.

### `/chat` `selected_slot` field

- When the graph is interrupted for HITL, the `/chat` response now includes:
  ```json
  "selected_slot": {
    "doctor_name": "...",
    "specialty": "...",
    "appointment_time": "...",
    "is_mock": true
  }
  ```
- The Streamlit HITL card reads this field to display specific booking details to the patient.

---

## Streamlit Appointments UI

### `📅 My Appointments` Tab (new)

Added to the patient navigation sidebar. Calls `GET /appointments/me` and renders:

**Scheduled appointments** (green border card):
- ✅ SCHEDULED badge
- Doctor name, specialty, appointment time, notes (where set)
- `created_at` timestamp
- ⚠️ Mock/demo disclaimer
- `🗑️ Cancel Appointment #N` button → calls `POST /appointments/{id}/cancel`
- Refreshes list automatically on successful cancellation

**Cancelled appointments** (greyed-out card):
- ❌ CANCELLED badge
- Read-only; no cancel button shown
- Doctor, specialty, appointment time preserved for history

**Refresh button**: `🔄 Refresh Appointments` forces a list re-fetch.

### HITL Confirmation Card (updated)

Replaced the generic `"Phase 3 HITL Workflow Demo"` warning with a slot-specific card:

```
📋 Appointment Approval Required
───────────────────────────────────────────
👨‍⚕️ Doctor    Dr. Alex Smith (Dermatologist)
🩺 Specialty  Dermatologist
🕒 Slot       tomorrow at 10:00 AM
⚠️ Mock/Demo availability — not a real booking provider.
───────────────────────────────────────────
[ ✅ Approve & Book Appointment ]  [ ❌ Reject Request ]
```

After approval: `"✅ Appointment approved and booked. Check 📅 My Appointments."`  
After rejection: `"Request rejected. No appointment was created."`

---

## Safety Precedence

Phase 4 deterministic safety precedence is **unchanged and fully enforced**:

```
User Input
    ↓
input_screening_node
    ↓
evaluate_red_flags() ← pure Python, runs BEFORE LLM
    ↓ (if triggered)               ↓ (if clean)
Deterministic Emergency          Supervisor / Scheduling Agent
Escalation                       HITL → Booking
(no LLM, no scheduling,
 no HITL, no booking)
```

**Red-flag terms (as of Phase 5):**
`chest pain`, `shortness of breath`, `can't breathe`, `cannot breathe`, `difficulty breathing`, `sudden numbness`, `sudden weakness`, `severe bleeding`, `unconscious`, `anaphylaxis`, `loss of consciousness`, `stroke symptoms`, `slurred speech`, `face drooping`, **`heart attack`** *(added M5)*, **`cardiac arrest`** *(added M5)*, **`stopped breathing`** *(added M5)*, **`not breathing`** *(added M5)*

---

## Patient Authorization / Security

| Authorization Check | Enforcement Point |
|---|---|
| Patient authentication required for `/appointments/me` | `auth.require_role("patient")` |
| Patient authentication required for `/appointments/{id}/cancel` | `auth.require_role("patient")` |
| Patient A cannot view Patient B's appointments | `GET /appointments/me` filters by `patient.user_id == current_user.id` |
| Patient A cannot cancel Patient B's appointment | `cancel_appointment()` queries by `patient_id` — returns `None` → 404 |
| Admin role cannot access patient appointment endpoints | Role guard returns 403 |
| No Streamlit direct DB access | All operations go through FastAPI REST endpoints |

---

## Test Results

### Automated Test Suite

```text
============================= test session starts ==============================
platform win32 -- Python 3.13.15, pytest-9.1.1

tests/test_graph.py::test_graph_compilation                           PASSED
tests/test_graph.py::test_triage_routing                              PASSED
tests/test_graph.py::test_emergency_routing                           PASSED
tests/test_graph.py::test_scheduling_hitl_interrupt_and_resume        PASSED
tests/test_graph.py::test_scheduling_hitl_rejection                   PASSED
tests/test_graph.py::test_records_and_reminders_routing               PASSED
tests/test_main.py::test_health_check                                 PASSED
tests/test_main.py::test_auth_and_access_flow                         PASSED
tests/test_main.py::test_login_invalid_credentials                    PASSED
tests/test_main.py::test_mock_llm_service                             PASSED
tests/test_main.py::test_chat_patient_mock_mode                       PASSED
tests/test_main.py::test_chat_unauthenticated_role                    PASSED
tests/test_main.py::test_chat_invalid_payload                         PASSED
tests/test_main.py::test_chat_error_mappings                          PASSED
tests/test_main.py::test_chat_scheduling_hitl_endpoint_flow           PASSED
tests/test_main.py::test_chat_approve_rejection_flow                  PASSED
tests/test_main.py::test_chat_approve_not_found                       PASSED
tests/test_scheduling.py::test_synthetic_slot_search                  PASSED
tests/test_scheduling.py::test_scheduling_approval_creates_db_record  PASSED
tests/test_scheduling.py::test_scheduling_rejection_no_db_record      PASSED
tests/test_scheduling.py::test_red_flag_bypasses_scheduling           PASSED
tests/test_scheduling.py::test_get_my_appointments_and_cancellation_flow PASSED
tests/test_triage.py::test_red_flag_emergency_escalation              PASSED
tests/test_triage.py::test_prompt_injection_safety_override_prevention PASSED
tests/test_triage.py::test_input_screening_length_limit               PASSED
tests/test_triage.py::test_non_emergency_triage_flow                  PASSED
tests/test_triage.py::test_prohibited_clinical_behavior_assertions    PASSED
tests/test_triage.py::test_grounded_knowledge_attribution             PASSED
tests/test_triage.py::test_audit_event_logging                        PASSED

======================= 29 passed, 6 warnings in 4.97s =======================
```

### E2E Verification (58/58 PASS)

| Section | Checks | Result |
|---|---|---|
| A. Patient Authentication | 4 | ✅ All passed |
| B. Scheduling Request & Slot Selection | 9 | ✅ All passed |
| C. HITL Approval Mechanics | 2 | ✅ All passed |
| D. Rejection Path — Zero DB Mutation | 3 | ✅ All passed |
| E. Approval Path — Exactly 1 Appointment | 7 | ✅ All passed |
| F. GET /appointments/me Fields | 9 | ✅ All passed |
| G. Appointment Cancellation | 5 | ✅ All passed |
| H. Follow-up GET Confirms Cancelled | 3 | ✅ All passed |
| I. Safety Precedence — Red-Flag Intercepts | 10 | ✅ All passed |
| J. Cross-Patient Authorization Isolation | 4 | ✅ All passed |
| K. DB Mutation Summary | 2 | ✅ All passed |

---

## Milestone 5 Spec-Compliance Fixes

Two issues were discovered during the Phase 5 Milestone 5 full regression that required minimal correction:

### 1. `created_at` missing from `AppointmentResponse`

**File:** `app/schemas_ai.py`  
**Issue:** The `created_at` column exists in the `Appointment` DB model but was not included in the API response schema.  
**Fix:** Added `created_at: Optional[datetime] = None` to `AppointmentResponse`. Added `from datetime import datetime`.  
**Impact:** `GET /appointments/me` and `POST /appointments/{id}/cancel` now return `created_at` in ISO datetime format.

### 2. Missing critical emergency terms in `RED_FLAG_PATTERNS`

**File:** `app/services/triage.py`  
**Issue:** `"heart attack"`, `"cardiac arrest"`, `"stopped breathing"`, and `"not breathing"` were absent from the deterministic red-flag list despite being unambiguous life-threatening emergencies.  
**Fix:** Added all four terms to `RED_FLAG_PATTERNS`.  
**Impact:** These terms now trigger immediate deterministic emergency escalation, preventing any scheduling or LLM processing.  
**Regression impact:** All 29 existing tests continue to pass.

---

## Scope Boundaries — Deferred Capabilities

The following were explicitly **not** implemented in Phase 5:

| Capability | Reason | Target Phase |
|---|---|---|
| Real Google Calendar integration | Deferred per PRD | Future phase |
| Appointment rescheduling | Deferred to keep scope focused | Future phase |
| Medication/reminder creation | Out of Phase 5 scope | Phase 6 |
| PostgreSQL Row-Level Security (RLS) | Deferred | Phase 8 |
| pgvector / semantic RAG | Deferred | Phase 7 |
| LangSmith tracing | Deferred | Phase 9 |
| Patient consent enforcement | Deferred | Phase 6/8 |
| Azure deployment | Deferred | Phase 10 |

---

## Phase 5 Completion Status

**Phase 5 — Scheduling Agent: ✅ COMPLETE**

**Phase 6 — Patient Data Tools: ⏳ PENDING (NOT STARTED)**
