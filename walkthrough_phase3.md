# HealthSync AI — Phase 3: LangGraph Foundation Walkthrough

## Phase 3 Objective
The primary goal of Phase 3 was to integrate **LangGraph** into HealthSync AI as the stateful multi-agent orchestration layer. This phase establishes typed workflow state schemas, intent-based conditional routing via a Supervisor node, checkpointing, and human-in-the-loop (HITL) approval workflows without prematurely building Phase 4+ specialized agent features or clinical logic.

---

## What Was Implemented

1. **State Schema (`HealthSyncState`)**: Built a JSON-serializable `TypedDict` capturing conversation parameters: `session_id`, `user_id`, `user_message`, `intent`, `confidence`, `extracted_entities`, `current_agent`, `approval_required`, `approval_status`, `response_draft`, `final_response`, and `is_mock`.
2. **Supervisor Node & Router**: Reused `get_llm_service()` from [`app/services/llm.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/services/llm.py) to perform structured intent classification, routing dynamically to 6 specialized stub nodes (`triage`, `scheduling`, `records`, `reminders`, `emergency`, `general`).
3. **MemorySaver Checkpointing**: Configured thread state persistence across conversation turns using user-scoped thread keys.
4. **HITL Interruption Workflow**: Implemented dynamic `interrupt()` inside the `scheduling` stub node. On scheduling queries, execution halts, returning `approval_required: True` and `approval_status: "pending"`.
5. **FastAPI Endpoints**:
   - `POST /chat`: Invokes the compiled LangGraph pipeline using thread configuration (`{"configurable": {"thread_id": ...}}`).
   - `POST /chat/approve`: Accepts `"approved"` or `"rejected"` decisions, resumes the paused graph thread using `Command(resume=...)`, and returns the final outcome.
6. **Streamlit UI HITL Controls**: Updated [`streamlit_app.py`](file:///d:/AI%20Agents/healthsync-ai-agent/streamlit_app.py) to display an inline warning prompt with `[ ✅ Approve Scheduling ]` and `[ ❌ Reject Request ]` buttons when approval is required, preventing duplicate actions.

---

## Architecture Flow

```
User Query (Streamlit)
  ↓
FastAPI POST /chat (Patient OAuth2 Guard)
  ↓
User-Scoped Thread Key (user_<user_id>_<session_id>)
  ↓
LangGraph Invocation
  ↓
Supervisor Node (Calls LLM service extract_intent())
  ↓
Conditional Edge (route_by_intent)
  ↓
┌────────────┬─────────────┬───────────┬───────────┬───────────┬───────────┐
│  triage    │ scheduling  │  records  │ reminders │ emergency │  general  │
└────────────┴──────┬──────┴───────────┴───────────┴───────────┴───────────┘
                    │ (approval_status == 'pending')
                    ↓
             interrupt() Pause
                    │
            State Saved in MemorySaver
                    │
   [ FastAPI /chat Returns approval_required = True ]
                    │
   [ User Clicks Approve / Reject in Streamlit ]
                    │
   [ FastAPI POST /chat/approve (Command(resume=...)) ]
                    │
            Resume Execution
                    ↓
             Responder Node
                    ↓
            Final Chat Response
```

---

## Files Created & Modified

### Files Created
- [`app/services/graph.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/services/graph.py): Defines `HealthSyncState`, nodes, router, `MemorySaver`, dynamic interrupts, and compiled graph.
- [`tests/test_graph.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_graph.py): Unit tests for graph compilation, intent routing, scheduling interrupts, and thread resumes.
- [`walkthrough_phase3.md`](file:///d:/AI%20Agents/healthsync-ai-agent/walkthrough_phase3.md): Phase 3 completion walkthrough documentation.

### Files Modified
- [`requirements.txt`](file:///d:/AI%20Agents/healthsync-ai-agent/requirements.txt): Added `langgraph>=0.1.0`.
- [`app/schemas_ai.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/schemas_ai.py): Added `session_id`, `ApprovalRequest`, and HITL flags in `ChatResponse`.
- [`app/main.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/main.py): Integrated graph execution into `/chat` and added `/chat/approve`.
- [`streamlit_app.py`](file:///d:/AI%20Agents/healthsync-ai-agent/streamlit_app.py): Updated UI to handle session IDs and render Approve/Reject controls.
- [`tests/test_main.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_main.py): Expanded test suite to cover graph chat routing and approval endpoints.
- [`tests/conftest.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/conftest.py): Isolated test runs to Mock mode.
- [`README.md`](file:///d:/AI%20Agents/healthsync-ai-agent/README.md): Updated project status to Phase 3 COMPLETE.
- [`HealthSync_task.md`](file:///d:/AI%20Agents/healthsync-ai-agent/HealthSync_task.md): Marked Phase 3 tasks as COMPLETE and recorded test results.

---

## Security & Thread Isolation Approach

1. **User-Scoped Thread Keys**: The backend constructs thread keys as `user_<current_user.id>_<session_id>`. This prevents Patient B from reading or resuming Patient A's graph checkpoints.
2. **API Secret Hardening**: `.env` is properly listed in `.gitignore`. No live credentials or API keys exist in git-tracked source code.

---

## Automated Test Results

Run command:
```bash
.venv\Scripts\python.exe -m pytest -v tests/
```

Results:
```text
======================= 17 passed, 5 warnings in 4.35s =======================
```
- [`tests/test_graph.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_graph.py): 6 tests passed
- [`tests/test_main.py`](file:///d:/AI%20Agents/healthsync-ai-agent/tests/test_main.py): 11 tests passed

---

## Manual / E2E Verification Results

Manual verification against live server (`http://127.0.0.1:8000` & `http://localhost:8501`):
1. **Normal Query (`"I have a fever..."`)**: `200 OK`, `intent: triage`, `approval_required: False`.
2. **Scheduling Query (`"I would like to schedule..."`)**: `200 OK`, `intent: scheduling`, `approval_required: True`, `approval_status: pending`.
3. **Rejection Decision (`decision: "rejected"`)**: `200 OK`, `approval_status: rejected`, message: `"Appointment request... was REJECTED by user."`
4. **Approval Decision (`decision: "approved"`)**: `200 OK`, `approval_status: approved`, message: `"Appointment request... has been APPROVED by user."`

---

## Explicit Scope Boundary

### IN SCOPE — Phase 3 (COMPLETE)
- LangGraph state schema definition (`TypedDict`).
- Supervisor node and conditional intent router.
- Skeleton stub nodes for specialized agents.
- `MemorySaver` thread checkpointing.
- HITL dynamic interruption on scheduling requests.
- Backend `/chat` and `/chat/approve` endpoint integration.
- Streamlit inline approval workflow UI.

### DEFERRED — Phase 4+
- Clinical triage rules, risk screening, and medical advice (Phase 4).
- RAG document ingestion & pgvector search (Phase 4 / Phase 7).
- Real appointment booking & calendar integrations (Phase 5).
- Patient records, vitals, and medication database persistence (Phase 6).
- PostgreSQL Row-Level Security (RLS) (Phase 8).
- LangSmith evaluation and tracing (Phase 9).

---

## Known Limitations

- **Transient Checkpointing**: `MemorySaver` uses in-memory process state. If the FastAPI backend server restarts, active conversation checkpoints are reset. Production database-backed checkpointers are deferred to later phases.

---

## Phase 4 Starting Point

When Phase 4 begins:
- The `triage` skeleton stub in [`app/services/graph.py`](file:///d:/AI%20Agents/healthsync-ai-agent/app/services/graph.py) will be replaced with the full **Triage Agent** implementation.
- Input screening, risk categorization (low/medium/high/emergency), and deterministic safety guardrails will be implemented inside the Triage flow.
