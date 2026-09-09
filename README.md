# CareGraph AI — Clinical Care Navigation & Scheduling Workflow

CareGraph AI is an LLM-routed care-coordination workflow with specialized deterministic nodes designed to support clinical care navigation, patient information access, scheduling, triage assistance, and related healthcare workflows. The current architecture employs a single LLM intent-classification decision (Supervisor router) followed by deterministic, specialized workflow nodes.

> **Note on Project Identity:** *CareGraph AI* is the official project identity. *(HealthSync AI was the internal development codename during Phases 1–10 Milestones 1–5).*
> **Compliance & Clinical Disclaimer:** HIPAA-aligned design; not a formally certified or audited HIPAA-compliant system. Not a medical device; for demonstration and research purposes only.

---

## Project Status

### **PHASE 1 — FOUNDATION: COMPLETE**
All core foundation features have been built and verified:
- **API Backbone**: FastAPI backend defining endpoints for user authentication, patient profiles, health status, and administrative list views.
- **Database Integration**: SQLAlchemy models mapping PostgreSQL tables for users and patient profile demographics.
- **Security**: Secure password hashing with bcrypt, JWT token creation, and role-based route protection.
- **Dashboard Interface**: Streamlit console providing user interfaces for demo accounts.
- **Testing Configuration**: Integrated SQLite environment via `conftest.py` ensuring serverless and isolated test execution.

### **PHASE 2 — AI FOUNDATION: COMPLETE**
Phase 2 integrates the AI coordination layer and intent classification:
- **Groq LLM Integration**: Implemented via the official `groq` SDK using environment variables (`GROQ_API_KEY` and `GROQ_MODEL=llama-3.3-70b-versatile`).
- **LLM Service Layer**: Abstracted through `BaseLLMService`, isolating Groq-specific client code and wrapping exceptions into clean decoupled domain exceptions.
- **Structured Output**: Standardized Pydantic schemas (`IntentEnum`, `IntentExtraction`) to validate JSON responses returned by Groq JSON Mode.
- **Mock Fallback Mode**: Integrates a deterministic keyword-based classifier executing when `GROQ_API_KEY` is not present (`is_mock: True`).

### **PHASE 3 — LANGGRAPH FOUNDATION: COMPLETE**
Phase 3 integrates the stateful workflow orchestration layer:
- **LangGraph State Schema**: Defined `CareGraphState(TypedDict)` (with `HealthSyncState` compatibility alias) containing JSON-serializable execution state attributes.
- **Supervisor & Conditional Routing**: Implemented Supervisor node routing requests based on intent classification (`triage`, `scheduling`, `records`, `reminders`, `emergency`, `general`) to specialized deterministic nodes.
- **MemorySaver Checkpointing**: State persistence across conversation turns configured with user-scoped `thread_id` keys.
- **Human-in-the-Loop (HITL) Interruption**: Dynamic `interrupt()` pauses graph execution when patient approval is required.
- **FastAPI Endpoints**: Integrated `POST /chat` with the graph pipeline and added `POST /chat/approve` to resume paused threads upon `"approved"` or `"rejected"` decisions.
- **Streamlit HITL Interface**: Integrated inline Approve/Reject workflow controls in Streamlit.

### **PHASE 4 — FIRST VERTICAL SLICE (TRIAGE NODE): COMPLETE**
Phase 4 implements the complete Triage vertical slice:
- **Deterministic Red-Flag Safety Engine**: Pure Python evaluator (`evaluate_red_flags()`) executing before LLM reasoning to force immediate 911/112/102 emergency escalation on life-threatening symptoms including chest pain, heart attack, cardiac arrest, difficulty breathing, stroke symptoms, and others.
- **Input Screening & Security**: Message length enforcement (max 2000 chars) and prompt injection override screening (`"ignore safety instructions"`).
- **Triage Node Core Logic**: Categorizes symptoms into `emergency`, `urgent`, and `non_urgent` risk levels and structures non-diagnostic care navigation advice and follow-up questions.
- **Local Grounded Knowledge Base**: Grounded retrieval attaching source attribution.
- **Structured Audit Logging**: Minimal audit event logger (`log_audit_event()`) storing workflow execution metadata without sensitive free text or PHI.
- **Streamlit Presentation**: Renders color-coded risk status badges, grounded source citations, and follow-up question chips.

### **PHASE 5 — FIRST VERTICAL SLICE (SCHEDULING NODE): COMPLETE**
Phase 5 implements the complete Scheduling vertical slice on top of the Phase 1–4 foundation:
- **Appointment Database Model**: `Appointment` table added to PostgreSQL with fields: `id`, `patient_id`, `doctor_name`, `specialty`, `appointment_time`, `status` (`scheduled`/`cancelled`), `notes`, `created_at`.
- **Synthetic Availability Provider**: `app/services/scheduling.py` provides `search_available_slots()` returning deterministic mock slots keyed by specialty/date preference.
- **LangGraph Scheduling Node**: Replaced Phase 3 HITL stub with a full `scheduling_node` that extracts intent entities, searches synthetic provider, selects slot, and calls `interrupt()` to pause the graph for patient approval.
- **Plan → Act → Verify DB Booking**: On approval, `book_appointment_slot()` calls `crud.create_appointment()` and verifies database persistence.
- **Appointment API Endpoints**: `GET /appointments/me` and `POST /appointments/{id}/cancel`.
- **Streamlit Appointments UI**: Added `📅 My Appointments` tab listing scheduled and cancelled appointments.

### **PHASE 6 — PATIENT DATA TOOLS: COMPLETE**
Phase 6 implements secure, patient-scoped data management tools:
- **Data Models**: Added `Medication`, `Vital`, and `MedicationReminder` SQLAlchemy models with foreign key constraints to `patients.id`.
- **Controlled Python Tool Layer (`app/services/patient_data.py`)**: 8 deterministic Python functions (profile, medications, vitals, trend calculations, reminder schedule, reminder creation, reminder cancellation).
- **Deterministic Vital Trends**: Pure Python numeric comparisons (`increasing`, `decreasing`, `stable`) for scalar vitals; skips compound blood pressure values.
- **FastAPI Endpoints**: 6 new endpoints (`GET/POST /vitals/me`, `GET /medications/me`, `GET/POST /reminders/me`, `POST /reminders/{id}/cancel`). Strictly protected by `require_role("patient")`.
- **LangGraph `patient_data_node`**: Unified node replacing stubs; dispatches based on intent (`RECORDS` vs `REMINDERS`).
- **Streamlit Patient Console**: Added `❤️ My Vitals`, `💊 My Medications`, and `⏰ My Reminders` tabs with interactive forms, tables, and medical disclaimers.

### **PHASE 7 — RAG & RETRIEVAL LAYER: COMPLETE**
Phase 7 implements grounded clinical care retrieval:
- **Knowledge Base Schema**: `KnowledgeDocument` table with JSON embedding representation and provenance metadata (`title`, `source`, `source_type`, `category`, `version`, `status`, `publication_date`). PostgreSQL `pgvector` extension setup is staged in schemas for future in-database vector indexing.
- **Embedding Service**: Deterministic hash-based lexical vector generator (`app/services/embeddings.py`) producing 384-dimensional unit-normalized dense vectors based on token hashing.
- **Vector Retrieval Layer**: Semantic search executing cosine similarity ranking in pure Python with NumPy (`app/services/vector_store.py`) and metadata filtering (`status="active"`, `category="triage"`).
- **LangGraph Triage Node RAG**: Grounded clinical retrieval directly injected into `triage_node` with source provenance attribution and safe out-of-domain degradation (`app/services/knowledge.py`, `app/services/graph.py`).
- **RAG Evaluation Suite**: 100% Top-1 accuracy on a 5-query internal smoke-test benchmark, 0 unsupported claims, 0% stale document leakage (`tests/test_rag_evaluation.py`).
- **Knowledge Base Content Transparency**: The documents indexed in the knowledge base are **synthetic curated care-navigation summaries** designed for care coordination demonstration and testing. They do not constitute authoritative medical literature or certified clinical guidelines.

### **PHASE 8 — SAFETY, SERVER-SIDE TOOL AUTHORIZATION & PATIENT CONSENT: COMPLETE**
Phase 8 establishes server-side tool access controls, patient privacy boundaries, and consent gates:
- **Server-Side Tool Authorization Engine (`app/services/security.py`)**: Enforces an explicit role-to-tool permission matrix (`ROLE_TOOL_PERMISSIONS`), strictly prohibiting the LLM from acting as an access-control authority.
- **Caller Identity Binding & Tenant Isolation**: Asserts caller authentication and verifies that patients can only access their own clinical records, preventing cross-patient data leaks.
- **Patient Consent Enforcement**: Requires active, unexpired consent (`verify_patient_consent()`) before executing protected patient data tools; denies access on expired or missing consent.
- **Minimum-Necessary Data Controls**: Automatically clamps bulk record queries to safe bounds (`MAX_RECORDS_LIMIT = 50`) and sanitizes parameter types and enums.
- **Structured Zero-PHI Audit Logging**: Emits structured audit events containing caller ID, action, and tool names with zero sensitive free text or PHI.
- **Compliance Scope**: HIPAA-aligned design; not a formally certified or audited HIPAA-compliant system.

### **PHASE 9 — OBSERVABILITY, ZERO-PHI TELEMETRY & EVALUATION: COMPLETE**
Phase 9 implements production telemetry, quantitative evaluation, and cost analytics:
- **Zero-PHI Sanitization Engine (`app/services/telemetry.py`)**: Recursive scrubbing of email addresses, phone numbers, authentication tokens, passwords, and sensitive dictionary fields before telemetry emission.
- **Non-Blocking Telemetry Tracing (`trace_span`)**: Span context manager tracking workflow execution, step latencies, token counts, and error states; metrics exposed via `GET /telemetry/metrics`.
- **Model Router Policy & Cost Intelligence (`app/services/llm.py`)**: Task-based model tiering, token cost tracking, and no-silent-escalation enforcement; token usage and cumulative cost analytics exposed via `GET /costs`.
- **Synthetic Benchmark Evaluation Harness (`app/services/evaluation.py`)**: Deterministic offline evaluation harness executing 55 benchmark scenarios (`app/data/evaluation_scenarios.json`) measuring intent accuracy, safety escalation, and latency.

### **PHASE 10 — PRODUCTION READINESS, DOCKER CONTAINERIZATION & CI/CD: COMPLETE**
Phase 10 establishes production containerization, CI/CD pipeline automation, and deployment configuration:
### **PHASE 11 — HL7 FHIR R4 INTEROPERABILITY & PROMETHEUS/GRAFANA OBSERVABILITY: COMPLETE**
Phase 11 establishes healthcare standard interoperability and enterprise monitoring:
- **HL7 FHIR R4 Interoperability Gateway (`app/services/fhir_client.py`, `app/services/fhir_adapter.py`)**: HL7 FHIR R4 interoperability with the public SMART Health IT reference sandbox; Epic/Cerner-specific connectivity is a documented future extension, with automatic LOINC mapping (BP, Heart Rate, SpO2, Weight, Temp), caching, retry backoff, and deterministic mock fallbacks.
- **Agent Node FHIR Integration**: `patient_data_node` and `scheduling_node` dynamically retrieve clinical records and synchronize appointments with FHIR EHR servers while strictly enforcing server-side `authorize_tool` and Consent Gates.
- **Enterprise Prometheus Observability (`app/services/observability.py`)**: Emits standard Prometheus Counters, Histograms, and Gauges tracking graph latency (p95/p50), intent distribution, red-flag safety escalations, token costs, and FHIR transactions with Zero PHI.
- **Dockerized Observability Stack**: Pre-configured Prometheus server (`:9090`) and Grafana dashboard (`:3000`) containerized in `docker-compose.yml` with automated datasource and dashboard JSON provisioning.
- **Developer Guide**: Comprehensive guide in `docs/FHIR_OBSERVABILITY_GUIDE.md` and configuration template `.env.fhir.example`.

### **PHASE 12 — TRUE MULTIMODAL AGENT FUSION & NOTIFICATION AUTOMATION: COMPLETE**
Phase 12 fuses previously isolated voice, vision, and messaging capabilities directly into the **LangGraph cognitive agent workflow**:
- **Agentic Voice-to-Voice Pipeline (`POST /chat/voice`)**: Patient speech audio is transcribed via in-memory Groq Whisper STT, injected directly into `graph.invoke()` for clinical reasoning and FHIR execution, and synthesized into a spoken audio stream via TTS.
- **Agentic Medical Document & Observation Analysis (`POST /chat/vision`)**: Patients upload prescriptions, lab reports, or vitals readings; the Vision service extracts clinical observations, merges them into the agent prompt, and coordinates records/triage routing under non-diagnostic safety boundaries.
- **Automated Outbound Appointment Confirmation**: On appointment approval in `/chat/approve`, the system automatically triggers an outbound SMS confirmation via `messaging.py` with appointment details.
- **Streamlit Multimodal Chat Console**: Direct microphone/audio file upload and playback + medical document upload widgets in the Patient Chat tab.

---

## Verified Test Results & Regression Baseline

- **Total Test Suite**: **237 passed, 0 failed, 1 warning** (100% pass rate).
- **Execution Command**: `pytest`
- **Execution Environment**: Python 3.13.15, SQLite in-memory test fixtures, FastAPI `TestClient`.
- **Zero-PHI Compliance**: All tests verify that raw audio, image bytes, patient identifiers, and phone numbers are never persisted to disk or emitted to unredacted logs.


CareGraph AI maintains an automated regression test suite verifying workflow routing, safety bounds, tool security, retrieval logic, FHIR interoperability, and Prometheus metrics:

```text
======================= 232 passed, 1 warning in 39.31s =======================
```

*(Historical progression: 69 tests passing at Phase 7; 129 tests across Phases 8–10; expanded to 232 backend tests at Phase 11 completion).*

### Verification & Testing Layer Distinctions

CareGraph AI clearly distinguishes between its testing and verification layers:
1. **Automated Backend Regression Suite (215 Tests)**: In-memory isolated pytest execution testing all API endpoints, graph orchestration, security matrices, telemetry redaction, RAG accuracy, and CI configuration.
2. **Frontend Contract & Smoke Tests (112 Tests)**: Node.js test suite (`node --test tests/*.test.mjs`) in `frontend/` validating authentication token parsing, route authorization matrices, API client mappings, and schema contracts. *(Note: These are logic/smoke tests and do not provide full regression coverage of React UI components or browser DOM rendering).*
3. **Synthetic Benchmark Evaluation (55 Scenarios)**: Offline evaluation harness (`app/services/evaluation.py`) executing diverse clinical scenarios against expected intent, safety escalation, and latency benchmarks.
4. **Local Docker Runtime Validation**: Live Docker Compose execution verifying inter-container networking, PostgreSQL persistence, backend `/health` (HTTP 200), and frontend UI reachability on local ports 8000 and 8501.
5. **Cloud Deployment Staging**: Container images, environment mappings, and CI/CD deployment jobs configured for Render staging.

### Test Suite Breakdown (Selected Highlights)

| Test Suite | Tests | Target Coverage & Invariants |
|---|---|---|
| `tests/test_main.py` | 11 | Phase 1–3: Healthcheck, OAuth2/JWT authentication, mock LLM mode, chat endpoints, HITL resume/approval flows |
| `tests/test_graph.py` | 6 | Phase 3: LangGraph state compilation, supervisor routing, interrupts, thread state recovery |
| `tests/test_triage.py` | 7 | Phase 4: Deterministic red-flag emergency escalation, prompt injection defense, grounded knowledge attribution, audit logging |
| `tests/test_scheduling.py` | 5 | Phase 5: Synthetic availability search, Plan→Act→Verify booking, HITL rejection/approval paths, appointment cancellation |
| `tests/test_patient_data_service.py` | 6 | Phase 6: Patient demographics, medications, vitals, trend calculation, medication reminders |
| `tests/test_patient_data_api.py` | 5 | Phase 6: Role-scoped REST API patient endpoints, cross-patient data isolation |
| `tests/test_patient_data_graph.py` | 6 | Phase 6: LangGraph unified patient data node, tool dispatch, red-flag precedence over records queries |
| `tests/test_knowledge_models.py` | 4 | Phase 7: KnowledgeDocument schema, metadata fields, vector embeddings, status filtering |
| `tests/test_vector_search.py` | 9 | Phase 7: 384-dimensional dense vector embeddings, cosine similarity ranking, index maintenance |
| `tests/test_rag_triage.py` | 4 | Phase 7: LangGraph triage RAG retrieval injection, source attribution, out-of-domain degradation |
| `tests/test_rag_evaluation.py` | 6 | Phase 7: Quantitative RAG smoke benchmarks (5-query Top-1 accuracy, zero hallucination, version filtering, emergency safety override) |
| `tests/test_telemetry.py` | 8 | Phase 9: Zero-PHI sanitization, trace span lifecycles, execution telemetry, cost metrics |
| `tests/test_tool_authorization.py` | 9 | Phase 8: Server-side tool authorization matrix, minimum-necessary data clamping, permission enforcement |
| `tests/test_model_routing_and_cost.py` | 6 | Phase 9: Model router policy, no-silent-escalation rules, token tracking and cost analytics |
| `tests/test_consent.py` | 6 | Phase 8: Patient consent verification, opt-in/opt-out gates, expired consent denial |
| `tests/test_evaluation_metrics.py` | 8 | Phase 9: Structured telemetry assertions, clinical grounding metrics, safety score computations |
| `tests/test_evaluation_suite.py` | 6 | Phase 9: Multi-scenario synthetic evaluation benchmark execution |
| `tests/test_production_config.py` | 4 | Phase 10: Production JWT validation, `.env.example` placeholder hygiene, `.gitignore` secret protection |
| `tests/test_ci_pipeline.py` | 13 | Phase 10: Dockerfile compliance, CI/CD pipeline schema, container healthcheck specifications |

### Phase 5 Scheduling Slice Live E2E Verification

During the completion of the Phase 5 scheduling vertical slice, a live E2E verification script was executed against the running FastAPI server — **58/58 checks passed**, validating the core scheduling, HITL approval/rejection paths, and red-flag safety intercepts:

| Category | Checks | Result |
|---|---|---|
| Patient Authentication | 4 | ✅ All passed |
| Scheduling Request & Slot Selection | 9 | ✅ All passed |
| HITL Approval Prompt Mechanics | 2 | ✅ All passed |
| Rejection Path — Zero DB Mutation | 3 | ✅ All passed |
| Approval Path — Exactly 1 Appointment | 7 | ✅ All passed |
| `GET /appointments/me` Fields & Structure | 9 | ✅ All passed |
| Appointment Cancellation | 5 | ✅ All passed |
| Follow-up GET Confirms Cancelled | 3 | ✅ All passed |
| Safety Precedence — Red-Flag Intercepts | 10 | ✅ All passed |
| Cross-Patient Authorization Isolation | 4 | ✅ All passed |
| Database Mutation Summary | 2 | ✅ All passed |

---

## Architecture Overview

```text
User Input
    ↓
Input Screening (max 2000 chars, injection detection)
    ↓
Deterministic Red-Flag Safety Check (evaluate_red_flags())
    ↓ (emergency)                      ↓ (safe)
Emergency Escalation          Intent Supervisor (Single LLM decision)
(no LLM, no scheduling)           ↓
                          ┌─────────────────────────────┐
                          │ Deterministic Node Dispatch │
                          │ (Triage / Sched. / Records) │
                          └─────────────────────────────┘
                                     ↓
                          Scheduling Node (Deterministic)
                                     ↓
                          search_available_slots()
                          (Synthetic/Mock Provider)
                                     ↓
                          interrupt() → HITL Pause
                                     ↓
                          Patient: Approve / Reject
                                     ↓
                          book_appointment_slot()
                          crud.create_appointment()
                          DB Verification
                                     ↓
                          Confirmed Response
```

---

## Synthetic/Mock Scheduling Disclaimer

> ⚠️ The scheduling provider in Phase 5 is **synthetic/mock** (`app/services/scheduling.py`). Appointments are stored in the local PostgreSQL database for demonstration purposes only. This is **not** a real medical booking system and does not connect to any real doctor, hospital, or calendar service. Real Google Calendar integration is deferred to a future phase.

---

## Technical Stack

- **Backend**: FastAPI, Uvicorn, Pydantic, SQLAlchemy.
- **Database**: PostgreSQL (SCRAM-SHA-256) with `appointments` table (schema staged for future pgvector migration).
- **Workflow Orchestration**: LangGraph (`StateGraph`, `MemorySaver`, `interrupt()`) with single LLM intent routing and specialized deterministic nodes.
- **LLM**: Groq API (`llama-3.3-70b-versatile`) with deterministic mock fallback.
- **Vector Retrieval**: Deterministic 384-dimensional lexical hash vectors with in-memory Python cosine similarity.
- **Authentication**: JWT (JSON Web Tokens), OAuth2 Bearer, Bcrypt password hashing.
- **Frontend**: Next.js 14 (App Router) & Streamlit console.
- **Testing**: Pytest (215 backend regression tests) + Node.js contract & smoke tests (112 tests; note: does not provide full React UI component DOM coverage).
- **Compliance Scope**: HIPAA-aligned design; not a formally certified or audited HIPAA-compliant system.

---

## Setup and Installation

### 1. Clone & Prepare virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in the details:
```bash
cp .env.example .env
```
Ensure your PostgreSQL server is active on `localhost:5432` and credentials in `.env` are correct.

---

## Running the Application

### 1. Run the FastAPI Backend
Start the FastAPI server:
```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
This will automatically connect to PostgreSQL, create the target database if it doesn't exist, build the relational tables, and seed the demo accounts.

### 2. Run the Streamlit Frontend
Launch the Streamlit console:
```bash
.venv\Scripts\streamlit.exe run streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser to interact with the application.

---

## Testing

Run the automated test suite to verify connectivity, database persistence, and authorization guards:
```bash
.venv\Scripts\python.exe -m pytest -v tests/
```
