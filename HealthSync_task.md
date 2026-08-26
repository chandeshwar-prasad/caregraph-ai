# HealthSync AI — Task Plan

**Source of truth:** `HealthSync_PRD.md`  
**PRD Version:** 2.0 — Final MVP Planning Baseline  
**Project:** HealthSync AI  
**Purpose:** Learning + implementation roadmap for building the HealthSync AI portfolio project.

> **Important:** This task plan is derived from the current `HealthSync_PRD.md`, especially Sections 44–45. The PRD is the architectural source of truth.

---

# 0. Project Guardrails

- [ ] Use synthetic healthcare data only.
- [ ] Do not use real patient/PHI data.
- [ ] Do not present HealthSync AI as an AI doctor.
- [ ] Do not build autonomous diagnosis or prescription functionality.
- [ ] Do not change medication prescriptions or dosages.
- [ ] Do not claim HIPAA/GDPR/DPDP certification.
- [ ] Use mock/sandbox integrations for the portfolio prototype.
- [ ] Never claim an external action succeeded without verified tool/API confirmation.
- [ ] Keep secrets/API keys out of GitHub.
- [ ] Minimize sensitive data in logs and traces.
- [ ] Treat prompt injection as a first-class security risk.
- [ ] Use deterministic safety rules for predefined high-risk patterns.
- [ ] Use human approval where required.
- [ ] Keep Patient + Admin as the only MVP roles.
- [ ] Do not create separate agents for CRUD/data-access capabilities.
- [ ] Agents reason/plan; controlled tools execute actions.
- [ ] Build vertical slices before expanding the system.

---

# Phase 1 — Foundation (COMPLETE)

**Status: COMPLETE**  
**Verified Phase 1 Test Results:**
- Automated backend tests in `tests/test_main.py` run against SQLite database pass successfully:
  - `test_health_check`: Passed
  - `test_auth_and_access_flow`: Passed
  - `test_login_invalid_credentials`: Passed
- Streamlit UI and FastAPI endpoints verified manually to work in sync.

---

## 1.1 Project Setup — Learning

- [x] Understand Python project structure.
- [x] Understand virtual environments.
- [x] Understand environment variables.
- [x] Understand `.env` and `.env.example`.
- [x] Understand dependency management.
- [x] Understand Git branches/commits at a practical level.
- [x] Understand why secrets must not be committed.

## 1.2 Repository

- [x] Create/prepare `healthsync-ai` GitHub repository.
- [x] Create initial README.
- [x] Add `.gitignore`.
- [x] Add `.env.example`.
- [x] Create `docs/`.
- [x] Add the current `HealthSync_PRD.md`.
- [x] Add architecture documentation.
- [x] Create initial project structure.
- [x] Make first clean commit.

## 1.3 FastAPI — Learning

- [x] Understand what an API is.
- [x] Understand REST.
- [x] Learn GET vs POST.
- [x] Learn JSON request/response.
- [x] Learn HTTP status codes.
- [x] Learn FastAPI basics.
- [x] Learn Pydantic models.
- [x] Learn request validation.
- [x] Learn basic exception handling.

## 1.4 FastAPI — Build

- [x] Create FastAPI application.
- [x] Create `/health`.
- [x] Create basic `/chat`.
- [x] Define request schema.
- [x] Define response schema.
- [x] Add validation.
- [x] Add basic error handling.
- [x] Test API locally.
- [x] Review generated API documentation.

## 1.5 PostgreSQL — Learning

- [x] Understand relational databases.
- [x] Understand tables/rows/columns.
- [x] Learn primary keys.
- [x] Learn foreign keys.
- [x] Learn relationships.
- [x] Learn basic SQL.
- [x] Learn SELECT.
- [x] Learn INSERT.
- [x] Learn UPDATE.
- [x] Learn DELETE.
- [x] Learn JOIN.
- [x] Understand indexes.
- [x] Understand transactions.
- [x] Understand migrations.

## 1.6 PostgreSQL — Initial Build

Start with only the tables needed by the current workflow.

Potential entities from the PRD:

- [x] users
- [x] patients
- [ ] patient_consents (Deferred to Phase 3/4)
- [x] appointments (Implemented in Phase 5)
- [ ] medications (Deferred to Phase 6)
- [ ] medication_schedules (Deferred to Phase 6)
- [ ] vitals (Deferred to Phase 6)
- [ ] lab_results (Deferred to Phase 6)
- [ ] encounters (Deferred to Phase 6)
- [ ] prescriptions (Deferred to Phase 6)
- [ ] documents (Deferred to Phase 6)
- [ ] reminders (Deferred to Phase 6)
- [ ] audit_logs (Deferred to Phase 6)
- [ ] agent_runs (Deferred to Phase 6)

- [x] Create database connection.
- [x] Create initial schema.
- [x] Add migrations.
- [x] Seed synthetic data.
- [x] Test basic queries.

## 1.7 Authentication — Initial

- [x] Understand authentication vs authorization.
- [x] Select authentication approach consistent with PRD.
- [x] Configure Supabase Auth or equivalent (using JWT token-based FastAPI OAuth2 Bearer).
- [x] Implement patient authentication.
- [x] Implement admin authentication.
- [x] Store only required identity information.

## 1.8 Streamlit — Learning

- [x] Learn Streamlit basics.
- [x] Learn forms.
- [x] Learn session state.
- [x] Learn tables.
- [x] Learn basic charts.
- [x] Learn page/navigation patterns.
- [x] Understand frontend-to-backend requests.

## 1.9 Streamlit — Build

- [x] Create HealthSync landing/home page.
- [x] Create login/demo access.
- [x] Create chat interface.
- [x] Create basic patient profile.
- [x] Connect Streamlit to FastAPI.
- [x] Display API responses.

## Phase 1 Exit Criteria

- [x] FastAPI runs locally.
- [x] PostgreSQL runs locally.
- [x] Streamlit communicates with FastAPI.
- [x] Synthetic patient data exists.
- [x] Basic authentication works.
- [x] No secrets are committed.
- [x] Project structure is understandable.

---

# Phase 2 — AI Foundation (COMPLETE)

**Status: COMPLETE**  
**Verified Phase 2 Test Results:**
- 8/8 automated test cases in `tests/test_main.py` pass.
- Manual verification of Mock mode and live Groq API connectivity is successful.
- Replay protection logic is verified.

**PRD alignment:** Groq API + structured outputs + model abstraction + basic chat.

## 2.1 LLM Fundamentals — Learning

- [x] Understand LLM API requests.
- [x] Understand system/user messages.
- [x] Understand structured outputs.
- [x] Understand token usage.
- [x] Understand latency.
- [x] Understand model cost.
- [x] Understand temperature/response variability at a level appropriate for MVP.
- [x] Understand API failures/timeouts.
- [x] Understand retries.

## 2.2 Groq Integration

- [x] Configure API key through environment variables (`GROQ_API_KEY`, `GROQ_MODEL`).
- [x] Create an LLM service layer (implemented in `app/services/llm.py`).
- [x] Add primary model (using `llama-3.3-70b-versatile`).
- [x] Build basic chat (via FastAPI `/chat` endpoint and Streamlit UI).
- [x] Add structured intent extraction.
- [x] Validate model output (validated via JSON Mode and Pydantic validation).
- [x] Add timeout handling.
- [ ] Add retry limits (Deferred to future resiliency updates).

## 2.3 Model Abstraction

Create an abstraction so the application is not tightly coupled to one provider.

Conceptually:

```text
Application
    ↓
Model Interface
    ├── Fast Model
    ├── Strong Model
    └── Embedding Model
```

- [x] Define model interface (`BaseLLMService` in `app/services/llm.py`).
- [x] Define model configuration.
- [x] Keep provider-specific code isolated.
- [x] Record model name/version where practical (default to `"llama-3.3-70b-versatile"`).
- [x] Do not add multiple providers just for appearance.

## 2.4 Basic Cost Tracking (Deferred to Phase 9)

- [ ] Capture token usage.
- [ ] Capture model used.
- [ ] Estimate cost per model call.
- [ ] Store usage metrics separately from sensitive healthcare content.
- [ ] Define placeholders for request/session limits.
- [ ] Mark numeric cost ceilings as **TBD during implementation** rather than inventing them prematurely.

## Phase 2 Exit Criteria

- [x] HealthSync can communicate with an LLM.
- [x] Structured outputs are validated.
- [x] Model calls are abstracted.
- [ ] Token/model usage can be observed (Deferred to Phase 9).
- [x] Basic chat works through the application.

---

# Phase 3 — LangGraph (COMPLETE)

**PRD alignment:** state schema + Supervisor + routing + conditional edges + checkpointing + pause/resume.
**Status: COMPLETE**

**Verified Phase 3 Test Results:**
- Automated test suite passing in SQLite environment: `17 passed, 5 warnings in 4.35s`
- [`tests/test_graph.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_graph.py): 6 passed
- [`tests/test_main.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_main.py): 11 passed
- Manual E2E verification verified against FastAPI server (`/chat`, `/chat/approve`) and Streamlit HITL UI.

## 3.1 LangGraph — Learning

- [x] Understand why LangGraph is useful.
- [x] Understand graph state.
- [x] Understand nodes.
- [x] Understand edges.
- [x] Understand conditional edges.
- [x] Understand workflow state.
- [x] Understand tool nodes.
- [x] Understand checkpointing.
- [x] Understand pause/resume.
- [x] Understand human-in-the-loop workflows.
- [x] Understand failure/retry paths.

## 3.2 Typed State Schema

Create explicit workflow state before building the complete graph.

Tasks:

- [x] Decide which fields are actually required.
- [x] Define typed state (`HealthSyncState(TypedDict)`).
- [x] Use TypedDict or Pydantic-compatible structures.
- [x] Minimize sensitive data in transient state.
- [x] Define allowed workflow statuses.
- [x] Define error states.

## 3.3 First Graph

Build progressively:

- [x] `START → LLM → END`
- [x] Add typed state.
- [x] Add intent classification.
- [x] Add conditional routing.
- [x] Add one controlled tool.
- [x] Add tool result to state.
- [x] Add final response node.

## 3.4 Supervisor

- [x] Create Supervisor node.
- [x] Route based on intent.
- [x] Route Triage requests.
- [x] Route Scheduling requests.
- [x] Route patient-data/reminder requests to controlled tools/services.
- [x] Handle unsupported requests.
- [x] Preserve minimum necessary context.
- [x] Handle failures.

## 3.5 Checkpointing

- [x] Understand LangGraph checkpointing.
- [x] Select a suitable checkpointer (`MemorySaver`).
- [x] Persist workflow state.
- [x] Define pause conditions.
- [x] Define resume conditions.
- [x] Test interrupted workflow recovery.

## 3.6 Human Approval State

- [x] Add `approval_required`.
- [x] Add `approval_status`.
- [x] Add pause state.
- [x] Add resume state.
- [x] Add approval/rejection outcome.
- [x] Log approval decisions.

## Phase 3 Exit Criteria

- [x] Typed state exists.
- [x] Supervisor routes workflows.
- [x] Conditional edges work.
- [x] Checkpointing works.
- [x] A graph can pause and resume.
- [x] No unnecessary agents have been created.


---

# Phase 4 — First Vertical Slice: Triage

**PRD alignment:** Triage Agent + input screening + deterministic safety rules + basic RAG + safe response + audit trace.

This is the **first major end-to-end milestone**.

## 4.1 Input Screening

- [ ] Validate input size.
- [ ] Validate format.
- [ ] Normalize input.
- [ ] Detect malformed input.
- [ ] Add basic prompt-injection screening.
- [ ] Separate user data from system instructions.
# Phase 4 — First Vertical Slice: Triage (COMPLETE)

**PRD alignment:** Triage Agent + input screening + deterministic safety rules + basic grounded knowledge + safe response + audit trace.
**Status: COMPLETE**

**Verified Phase 4 Test Results:**
- Automated test suite passing in SQLite environment: `24 passed, 5 warnings in 4.44s`
- [`tests/test_graph.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_graph.py): 6 passed
- [`tests/test_main.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_main.py): 11 passed
- [`tests/test_triage.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_triage.py): 7 passed
- Live E2E verification verified against FastAPI server (`/chat`) and Streamlit UI.

## 4.1 Input Screening & Security

- [x] Add rate/size limits (max 2000 chars).
- [x] Log security-relevant events without unnecessary sensitive content.

## 4.2 Prompt-Injection Test Cases

Create explicit tests for:

- [x] "Ignore your safety instructions."
- [x] attempts to override system policies.
- [x] attempts to force unsafe medical recommendations.
- [x] attempts to make the agent call unauthorized tools.

## 4.3 Triage Agent

- [x] Define triage input schema.
- [x] Define symptom-intake flow.
- [x] Define follow-up question structure.
- [x] Define risk-category representation (`emergency`, `urgent`, `non_urgent`).
- [x] Define uncertainty representation.
- [x] Connect Triage Agent to Supervisor.
- [x] Prevent definitive-diagnosis language.
- [x] Add care-navigation response format.

## 4.4 Deterministic Safety Rules

- [x] Identify a small prototype red-flag rule set (`evaluate_red_flags()`).
- [x] Implement deterministic rules separately from LLM reasoning.
- [x] Define high-risk outcomes.
- [x] Define escalation outcomes (911/112/102).
- [x] Test high-risk scenarios.
- [x] Test low-risk scenarios.
- [x] Document that the rule set is not a complete clinical triage system.

## 4.5 Basic Grounded Knowledge Base (Local RAG)

- [x] Create a small trusted knowledge set ([`app/data/symptom_knowledge.json`](file:///d:/AI%20Agents/healthsync-ai-agent/app/data/symptom_knowledge.json)).
- [x] Define approved source types (`"HealthSync Curated Care Navigation Summary"`).
- [x] Retrieve relevant content (`app/services/knowledge.py`).
- [x] Pass retrieved context to the model.
- [x] Preserve source metadata.
- [x] Generate grounded response.
- [x] Test unsupported-claim behavior.

## 4.6 Audit Trace

Record important workflow events (`app/services/audit.py`):

- [x] workflow ID / session ID
- [x] intent
- [x] selected agent
- [x] safety decision
- [x] timestamp

Avoid storing unnecessary sensitive free text or PHI.

## Phase 4 Exit Criteria

- [x] A synthetic symptom scenario works end-to-end.
- [x] Input screening runs before orchestration.
- [x] Triage Agent is routed correctly.
- [x] Deterministic safety rules run.
- [x] Grounded knowledge base provides attributed information.
- [x] Unsafe/high-risk scenarios escalate.
- [x] Audit trace exists.
- [x] The workflow can be demonstrated without real patient data.


---

# Phase 5 — Scheduling Agent (COMPLETE)

**PRD alignment:** Scheduling Agent + mock availability + HITL approval + booking + verification + cancellation.
**Status: COMPLETE**

**Verified Phase 5 Test Results:**
- Automated test suite passing in SQLite environment: `29 passed, 6 warnings in 4.97s`
  - [`tests/test_graph.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_graph.py): 6 passed
  - [`tests/test_main.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_main.py): 11 passed
  - [`tests/test_triage.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_triage.py): 7 passed
  - [`tests/test_scheduling.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_scheduling.py): 5 passed
- Live E2E verification against FastAPI server: **58/58 checks passed** across authentication, HITL, approval, rejection, appointment listing, cancellation, safety precedence, and patient isolation checks.
- Two spec-compliance fixes applied during Milestone 5 verification:
  1. Added `created_at: Optional[datetime]` to `AppointmentResponse` in `app/schemas_ai.py` (field existed in DB model but was absent from API response schema).
  2. Added `"heart attack"`, `"cardiac arrest"`, `"stopped breathing"`, and `"not breathing"` to `RED_FLAG_PATTERNS` in `app/services/triage.py` (critical deterministic emergency terms were missing from the original list).

## 5.1 Scheduling Agent

- [x] Define appointment request schema (`AppointmentResponse` in `app/schemas_ai.py`).
- [x] Define scheduling state (`selected_slot`, `approval_required`, `approval_status` fields in `HealthSyncState`).
- [x] Define selected slot (returned as `dict` with `doctor_name`, `specialty`, `appointment_time`, `is_mock`).
- [x] Define approval status (`pending`, `approved`, `rejected`).
- [x] Define booking result (appointment `id` and status returned from DB).
- [x] Define verification result (DB re-query confirms row exists before confirmation).
- [x] Connect Scheduling Agent to Supervisor (`scheduling_node` in `app/services/graph.py`).

## 5.2 Mock Scheduling Tools

- [x] `search_available_slots()` — returns deterministic synthetic slots keyed by specialty/date.
- [x] `book_appointment_slot()` — calls `crud.create_appointment()` and verifies DB insertion.
- [x] `cancel_appointment()` via `POST /appointments/{id}/cancel` endpoint.
- [x] Create synthetic availability (`app/services/scheduling.py`, `Mock Demo Availability Provider`).
- [x] Validate tool arguments (specialty extracted from LLM entities).
- [x] Validate tool results (DB re-query before confirmation response).
- [ ] `reschedule_appointment()` — deferred to a later phase.
- [ ] `create_reminder()` — deferred to Phase 6.
- [ ] Handle unavailable slots — deferred (synthetic provider always returns a slot for Phase 5).

## 5.3 Approval + Checkpointing

- [x] Present appointment options (slot details shown in HITL confirmation card).
- [x] Ask for required confirmation (patient sees doctor/specialty/time before approving).
- [x] Pause graph (LangGraph `interrupt()` in `scheduling_node`).
- [x] Persist checkpoint (`MemorySaver` preserves state across pause/resume).
- [x] Accept approval (`POST /chat/approve` with `decision: "approved"`).
- [x] Accept rejection (`POST /chat/approve` with `decision: "rejected"`).
- [x] Resume graph (`Command(resume=...)` resumes the interrupted node).
- [x] Stop safely after rejection (no DB mutation on rejection, confirmed by E2E test D3).

## 5.4 Booking Verification

Implemented Plan → Act → Verify → Report flow:

```text
Plan  (extract specialty/date from user intent)
 ↓
Act   (search_available_slots → interrupt → patient approves)
 ↓
Verify (book_appointment_slot: create_appointment + DB re-query)
 ↓
Report (confirmed response includes appointment ID and slot details)
```

- [x] Verify booking response (confirmation message includes doctor, specialty, time, appointment ID).
- [x] Verify appointment ID/status (re-queried from DB before returning confirmation).
- [x] Verify stored appointment (`GET /appointments/me` returns the new record).
- [x] Never claim success without confirmation (booking failure raises exception; no confirmation sent).
- [ ] Test partial failures — deferred.
- [ ] Test duplicate requests — deferred.

## 5.5 Calendar Integration

- [ ] Evaluate Google Calendar API — deferred to a future phase.
- [ ] Create test/sandbox credentials — deferred.
- [ ] Implement availability — deferred.
- [ ] Implement event creation — deferred.
- [ ] Implement rescheduling — deferred.
- [ ] Implement cancellation (real calendar) — deferred.
- [ ] Add reminder workflow — deferred to Phase 6.

> Phase 5 uses a synthetic/mock availability provider (`Mock Demo Availability Provider`). Real calendar integration is explicitly deferred.

## 5.6 Vertical Slice 2 Demo

The Phase 5 demo workflow is implemented and verified:

```text
Scheduling Agent
 ↓
Availability Tool (search_available_slots — synthetic/mock)
 ↓
User Reviews Slot (HITL card shows doctor/specialty/time/mock disclaimer)
 ↓
Approval (POST /chat/approve: approved)
 ↓
Booking (book_appointment_slot → crud.create_appointment)
 ↓
Verification (DB re-query confirms row exists)
 ↓
Confirmed Response (appointment ID + slot details)
 ↓
Appointments UI (GET /appointments/me → 📅 My Appointments tab)
 ↓
Cancellation (POST /appointments/{id}/cancel → status: cancelled)
```

## Phase 5 Exit Criteria

- [x] Appointment search works (synthetic slots returned by `search_available_slots()`).
- [x] Appointment booking works in mock/sandbox (DB-verified via `book_appointment_slot()`).
- [x] Approval pauses/resumes workflow (LangGraph `interrupt()` + `Command(resume=...)`).
- [x] Booking is verified (DB re-query before confirmation; failure never produces false success).
- [ ] Reminder is created — deferred to Phase 6.
- [x] Failure does not produce a false success message (rejection path verified: 0 DB mutations).

---

# Phase 6 — Patient Data Tools

**PRD alignment:** Patient Data Services are controlled tools/services, NOT additional agents.

> **Do not create Care Agent, Records Agent, Medication Agent, or Vitals Agent for simple CRUD/data operations.**

## 6.1 Patient Record Tools

- [x] `get_patient_profile()`
- [ ] `get_patient_timeline()` (deferred within Phase 6)
- [ ] `get_encounters()` (deferred within Phase 6)
- [ ] `get_lab_results()` (deferred within Phase 6)
- [x] `get_medications()`

## 6.2 Vitals Tools

- [x] `get_vitals()`
- [x] `store_vital()`
- [x] `calculate_trend()`

Use SQL/Python for deterministic calculations.

## 6.3 Medication/Reminder Tools

- [x] `get_medication_schedule()`
- [x] `create_medication_reminder()`
- [ ] `update_reminder()` (deferred within Phase 6)
- [x] `cancel_reminder()`

- [x] Validate reminder schedule.
- [x] Never change medication instructions through the agent.
- [x] Store reminder status.

## 6.4 Record Summary

- [x] Retrieve authorized records.
- [ ] Retrieve relevant documents. (Phase 7 RAG)
- [x] Pass only relevant context to the model.
- [x] Preserve dates/source metadata.
- [x] Clearly distinguish stored facts from generated summaries.

## 6.5 Authorization

Every sensitive data tool must check:

```text
Authentication
 ↓
Authorization
 ↓
Consent
 ↓
Minimum Necessary
 ↓
Tool Execution
```

## Phase 6 Exit Criteria

- [x] Patient records can be retrieved through tools.
- [x] Vitals can be retrieved.
- [x] Trends can be calculated deterministically.
- [x] Medication reminders work.
- [x] No CRUD functionality has been turned into unnecessary agents.
- [x] Unauthorized access is blocked.

---

# Phase 7 — pgvector & RAG

**PRD alignment:** embeddings + pgvector + document ingestion + retrieval + source metadata + knowledge versioning + evaluation.

## 7.1 Embeddings — Learning

- [x] Understand what embeddings are.
- [x] Understand semantic similarity.
- [x] Understand vector search.
- [x] Understand embedding dimensions at a high level.
- [x] Understand metadata filtering.
- [x] Understand why structured data remains relational.

## 7.2 pgvector

- [x] Enable pgvector in PostgreSQL.
- [x] Create embeddings table.
- [x] Store vectors.
- [x] Store source metadata.
- [x] Implement semantic similarity search.
- [x] Add metadata filtering.
- [x] Connect retrieval to RAG.

## 7.3 Structured vs Vector Data

Keep structured facts in PostgreSQL:

```text
patient_id
appointment_date
medication
dose
blood_pressure
lab_value
```

Use pgvector for semantic/unstructured retrieval:

```text
medical knowledge document
approved information
synthetic patient document
```

- [x] Test that structured queries use SQL.
- [x] Test that semantic queries use vector retrieval.

## 7.4 Knowledge Base Metadata

Each document should include:

- [x] source
- [x] title
- [x] publication/update date when available
- [x] ingestion date
- [x] version
- [x] document status
- [x] region
- [x] content category

## 7.5 Knowledge Versioning

- [x] Define document statuses.
- [x] Define how a document becomes stale.
- [x] Allow controlled/manual status changes where appropriate.
- [x] Identify superseded documents.
- [x] Prevent silently treating old healthcare information as current.
- [x] Add re-indexing/update process.

## 7.6 Hybrid Retrieval

Only after basic semantic retrieval works:

- [x] Evaluate keyword + vector retrieval.
- [x] Add metadata filtering.
- [x] Evaluate reranking.
- [x] Keep hybrid retrieval only if it improves results.

## 7.7 RAG Evaluation

- [x] Build synthetic evaluation questions.
- [x] Measure retrieval relevance.
- [x] Measure groundedness.
- [x] Measure source coverage.
- [x] Measure unsupported claims.
- [x] Evaluate Ragas after the core RAG workflow is stable.

## Phase 7 Exit Criteria

- [x] pgvector works.
- [x] RAG retrieves relevant content.
- [x] Sources are traceable.
- [x] Knowledge versions/statuses are stored.
- [x] RAG evaluation exists.
- [x] Structured data is not incorrectly stored as vectors.

---

# Phase 8 — Safety & Security

**PRD alignment:** prompt-injection tests + tool authorization + consent enforcement + RBAC + RLS + audit hardening.

## 8.1 Tool Authorization

- [ ] Define tool permission matrix.
- [ ] Define which tools require patient authorization.
- [ ] Validate tool arguments.
- [ ] Check authorization before execution.
- [ ] Check consent where applicable.
- [ ] Check minimum-necessary data.
- [ ] Log authorization outcome.
- [ ] Test unauthorized tool calls.

## 8.2 Consent Enforcement

Consent must be enforced, not merely stored.

For sensitive patient-data access:

- [ ] authenticate user
- [ ] verify authorized role
- [ ] verify patient/resource ownership or permitted relationship
- [ ] check applicable consent
- [ ] apply minimum-necessary rule

- [ ] Test denied consent.
- [ ] Test missing consent.
- [ ] Test unauthorized patient access.

## 8.3 Authentication & RBAC

MVP roles:

### Patient

- [ ] Can access authorized personal data.
- [ ] Can perform permitted actions.
- [ ] Cannot access another patient.

### Admin

- [ ] Can manage synthetic demo data.
- [ ] Can manage knowledge-base content.
- [ ] Can inspect controlled audit/system information.
- [ ] Does not automatically get unrestricted patient-data access.

Future roles — **not MVP**:

- [ ] caregiver
- [ ] care coordinator
- [ ] healthcare staff
- [ ] clinician

## 8.4 PostgreSQL RLS

Learn:

- [ ] What Row-Level Security is.
- [ ] Why application authorization alone is insufficient.
- [ ] How PostgreSQL policies work.
- [ ] How application identity can be mapped to policies.

Build:

```text
User
 ↓
FastAPI
 ↓
PostgreSQL
 ↓
RLS Policy
 ↓
Authorized Rows Only
```

- [ ] Create RLS policy for patient-owned records.
- [ ] Create/update policies as required.
- [ ] Test Patient A cannot access Patient B.
- [ ] Test unauthorized updates.
- [ ] Test admin boundaries.
- [ ] Combine RLS with application authorization.

## 8.5 Prompt-Injection Security

- [ ] Maintain adversarial test set.
- [ ] Test instruction override.
- [ ] Test tool-call manipulation.
- [ ] Test unauthorized patient-data requests.
- [ ] Test malicious retrieved documents.
- [ ] Test malicious uploaded documents.
- [ ] Test output validation.
- [ ] Test constrained tool schemas.

## 8.6 Audit Hardening

Audit:

- [ ] input-screening outcome
- [ ] intent
- [ ] supervisor decision
- [ ] selected agent
- [ ] selected model
- [ ] retrieved source IDs
- [ ] tool request
- [ ] authorization decision
- [ ] tool result status
- [ ] safety decision
- [ ] approval decision
- [ ] final workflow outcome

- [ ] Avoid unnecessary sensitive free-text logging.
- [ ] Define retention expectations.

## Phase 8 Exit Criteria

- [ ] Unauthorized data access is blocked.
- [ ] Tool calls require authorization.
- [ ] Consent is checked at access time.
- [ ] RLS provides database-level defense in depth.
- [ ] Prompt-injection tests exist and pass defined expectations.
- [ ] Audit trail is meaningful without unnecessary PHI.

---

# Phase 9 — Observability & Evaluation

**PRD alignment:** LangSmith + evaluation dataset + RAG evaluation + agent evaluation + safety tests + cost tracking.

## 9.1 LangSmith / Observability

- [ ] Set up development-time tracing.
- [ ] Trace graph execution.
- [ ] Trace model calls.
- [ ] Trace tool calls.
- [ ] Trace workflow state where appropriate.
- [ ] Track latency.
- [ ] Track failures.
- [ ] Track token usage.
- [ ] Track safety decisions.

## 9.2 Sensitive Data Protection in Traces

- [ ] Identify sensitive trace fields.
- [ ] Redact/minimize sensitive content.
- [ ] Define observability retention.
- [ ] Review traces manually for accidental sensitive-data leakage.

## 9.3 Evaluation Dataset

Create synthetic scenarios for:

- [ ] simple health-information request
- [ ] low-risk symptom scenario
- [ ] high-risk scenario
- [ ] ambiguous symptom scenario
- [ ] appointment search
- [ ] appointment booking
- [ ] appointment rescheduling
- [ ] medication reminder
- [ ] record retrieval
- [ ] unauthorized access
- [ ] prompt injection
- [ ] tool failure
- [ ] RAG failure

## 9.4 Agent Evaluation

Measure:

- [ ] intent classification
- [ ] routing accuracy
- [ ] agent selection
- [ ] tool selection
- [ ] workflow completion
- [ ] failure recovery

## 9.5 RAG Evaluation

Measure:

- [ ] retrieval relevance
- [ ] grounded-response quality
- [ ] source coverage
- [ ] unsupported-claim rate

## 9.6 Safety Evaluation

Test:

- [ ] high-risk scenarios
- [ ] low-risk scenarios
- [ ] ambiguous scenarios
- [ ] prompt injection
- [ ] unauthorized tool requests
- [ ] false reassurance
- [ ] unsupported medical claims

## 9.7 System Evaluation

Measure:

- [ ] latency
- [ ] API failure rate
- [ ] workflow failure rate
- [ ] model usage
- [ ] cost per workflow
- [ ] verification success rate

## 9.8 Model Router Evaluation

- [ ] Compare fast vs strong model for representative tasks.
- [ ] Measure quality.
- [ ] Measure latency.
- [ ] Measure cost.
- [ ] Measure reliability.
- [ ] Define routing rules.
- [ ] Define low-confidence behavior.
- [ ] Add a documented fallback/default model.
- [ ] Do not silently escalate to expensive models.

## Phase 9 Exit Criteria

- [ ] Workflow traces are available.
- [ ] Sensitive data is minimized in traces.
- [ ] Evaluation dataset exists.
- [ ] Agent/RAG/safety evaluations can be repeated.
- [ ] Model usage and cost are measurable.
- [ ] Model routing has documented behavior.

---

# Phase 10 — Deployment

**PRD alignment:** Docker/containerization + Azure + secrets management + monitoring + production-like demo.

## 10.1 Containerization — Learning

- [ ] Understand Docker basics.
- [ ] Understand images.
- [ ] Understand containers.
- [ ] Understand Dockerfile.
- [ ] Understand environment variables.
- [ ] Understand container networking at a basic level.

## 10.2 Build

- [ ] Create FastAPI Dockerfile.
- [ ] Containerize backend.
- [ ] Decide frontend deployment approach.
- [ ] Test containers locally.
- [ ] Configure environment variables.
- [ ] Test health endpoint in container.

## 10.3 Azure — Learning

- [ ] Understand Azure resources.
- [ ] Understand App Service.
- [ ] Understand Azure Container Apps.
- [ ] Understand managed PostgreSQL options.
- [ ] Understand secrets/configuration.
- [ ] Understand monitoring.

## 10.4 Azure Deployment

- [ ] Select Azure App Service or Container Apps.
- [ ] Create required Azure resources.
- [ ] Configure environment variables securely.
- [ ] Configure secrets.
- [ ] Configure database.
- [ ] Deploy backend.
- [ ] Deploy frontend.
- [ ] Test authentication.
- [ ] Test primary workflow.
- [ ] Test scheduling sandbox/mock.
- [ ] Test failure handling.

## 10.5 Security

- [ ] No API keys in repository.
- [ ] Use secure secret management.
- [ ] Review database exposure.
- [ ] Review network access.
- [ ] Review logs for sensitive data.
- [ ] Review authentication/authorization in deployed environment.

## 10.6 Monitoring

- [ ] Configure application monitoring.
- [ ] Monitor errors.
- [ ] Monitor latency.
- [ ] Monitor resource usage.
- [ ] Monitor workflow failures.
- [ ] Document basic incident/failure behavior.

## Phase 10 Exit Criteria

- [ ] HealthSync runs in Azure.
- [ ] Core demo workflow works remotely.
- [ ] Secrets are protected.
- [ ] Monitoring exists.
- [ ] Deployment steps are documented.
- [ ] Prototype limitations are clearly visible.

---

# Phase 11 — Portfolio Extensions

**Only begin after the MVP is stable.**

## 11.1 Power BI

- [ ] Export/surface synthetic operational data.
- [ ] Build appointment KPIs.
- [ ] Build triage/workflow KPIs.
- [ ] Build agent-performance metrics.
- [ ] Build safety/escalation metrics.
- [ ] Build model usage/cost metrics.
- [ ] Connect the AI workflow to analytics.

Target narrative:

```text
AI Agent
 ↓
Operational Data
 ↓
PostgreSQL
 ↓
Power BI
 ↓
Operational Insights
```

## 11.2 Voice

- [ ] Speech-to-text.
- [ ] Voice response.
- [ ] Voice-specific safety handling.

## 11.3 Vision / Document Extraction

- [ ] Document upload.
- [ ] OCR.
- [ ] Structured extraction.
- [ ] Source validation.
- [ ] Prompt-injection testing for uploaded documents.

## 11.4 Communication

- [ ] SMS.
- [ ] WhatsApp.

## 11.5 Frontend Upgrade

- [ ] Evaluate Next.js only if Streamlit becomes limiting.
- [ ] Reuse FastAPI/backend architecture.

## 11.6 Additional Models

- [ ] Evaluate another provider.
- [ ] Compare capability.
- [ ] Compare cost.
- [ ] Compare latency.
- [ ] Compare reliability.
- [ ] Add only if measurable benefit exists.

## 11.7 Healthcare Interoperability

- [ ] Explore FHIR resources.
- [ ] Explore sandbox FHIR APIs.
- [ ] Explore hospital/EHR integration.
- [ ] Keep full FHIR server outside current MVP.

## Future Roles

- [ ] caregiver
- [ ] care coordinator
- [ ] healthcare staff
- [ ] clinician

These remain outside the MVP.

---

# Primary MVP Demo — Final End-to-End Test

Use the PRD's primary portfolio scenario:

> "I've had persistent cough and fever for three days. I want to know what I should do and, if appropriate, find a doctor tomorrow."

Expected workflow:

```text
User
 ↓
Input Screening
 ↓
Supervisor
 ↓
Triage Agent
 ↓
Deterministic Safety Rules
 ↓
RAG / Trusted Knowledge
 ↓
Safe Care Navigation Response
 ↓
User Requests Appointment
 ↓
Supervisor
 ↓
Scheduling Agent
 ↓
Availability Tool
 ↓
User Selects Slot
 ↓
Human / Policy Approval if Required
 ↓
Booking Tool
 ↓
Booking Verification
 ↓
Reminder Tool
 ↓
Verified Final Response
 ↓
Audit + Checkpoint Trace
```

## Final Demo Checklist

- [x] Input screening works.
- [x] Supervisor routes correctly.
- [x] Triage Agent works.
- [x] Deterministic safety rules work.
- [x] RAG retrieves relevant trusted information.
- [x] Response is grounded.
- [x] Scheduling Agent works.
- [x] Approval pauses/resumes workflow.
- [x] Booking tool works in mock/sandbox.
- [x] Booking is verified.
- [ ] Reminder is created — deferred to Phase 6.
- [x] Audit trace exists (Phase 4 `log_audit_event()`).
- [x] Failure paths are safe.
- [x] No real patient data is used.

---

# MVP Definition of Done

The MVP is complete when:

- [x] Patient can authenticate.
- [x] Patient can submit a healthcare-related request.
- [x] Input screening runs before orchestration.
- [x] Supervisor identifies/routes the task.
- [x] Triage Agent completes the first vertical slice.
- [x] Deterministic safety rules are active.
- [x] RAG retrieves trusted information.
- [x] PostgreSQL stores synthetic patient data.
- [ ] pgvector supports semantic retrieval — deferred to Phase 7.
- [x] Scheduling Agent searches availability.
- [x] Controlled tool creates an appointment in sandbox/mock environment.
- [x] Important actions are verified.
- [x] Human approval can pause/resume workflow.
- [x] Audit logs capture important workflow events.
- [x] Prompt-injection scenarios have been tested.
- [ ] Model usage/cost can be observed — deferred to Phase 9.
- [x] Core workflow works end-to-end.
- [x] Project runs locally.
- [ ] Project has documented deployment path — deferred to Phase 10.
- [x] README and architecture documentation are complete.
- [x] Demo clearly states that this is a synthetic-data prototype.
- [x] MVP does not contain unnecessary extra agents.

---

# Recommended Learning Rule

Do not try to learn every technology before building.

Follow this principle:

```text
Need arises
    ↓
Learn the concept
    ↓
Build the smallest useful version
    ↓
Test it
    ↓
Document what you learned
    ↓
Move to the next workflow
```

For unfamiliar technologies—especially PostgreSQL, LangGraph, pgvector, RAG, RLS, authentication, model routing and Azure—the goal is not to master the technology first.

The goal is to understand enough to build the next HealthSync component correctly.

---

# Most Important Project Rule

> **Do not build HealthSync AI as a collection of technologies. Build it as a sequence of safe, grounded, observable healthcare workflows.**

The progression is:

```text
One request
   ↓
One workflow
   ↓
One working agent
   ↓
One safety boundary
   ↓
One verified action
   ↓
One observable trace
   ↓
Then expand
```

The first meaningful goal is:

> **Build one safe, grounded, observable healthcare workflow end-to-end.**

Once that works, expand HealthSync AI from a working core rather than from disconnected architecture components.
