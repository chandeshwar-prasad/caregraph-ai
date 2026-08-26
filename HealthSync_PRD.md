# HealthSync AI — Product Requirements Document (PRD)

**Version:** 2.0  
**Status:** Final MVP Planning Baseline  
**Product:** HealthSync AI  
**Positioning:** Multi-Agent, Multi-Model Healthcare Navigation & Care-Management Assistant  
**Primary Markets:** India, USA, European Union  
**Prototype Data Policy:** Synthetic healthcare data only

---

# 1. Executive Summary

HealthSync AI is a healthcare coordination assistant designed to help patients navigate common healthcare workflows through one intelligent, action-oriented interface.

HealthSync AI is **not an AI doctor** and is not intended to autonomously diagnose diseases, prescribe treatment, change prescriptions, or replace healthcare professionals.

The system focuses on healthcare navigation and coordination:

- symptom and care navigation
- appointment search and management
- medication reminders
- health-record retrieval
- health-information retrieval
- simple health trends
- follow-up coordination

The core design principle is:

> **Understand → Screen → Route → Retrieve → Reason → Act → Verify → Respond → Audit**

HealthSync AI uses:

- a LangGraph-based Supervisor
- specialized Triage and Scheduling Agents
- controlled tools/services for patient records, medications, vitals and reminders
- task-appropriate model routing
- RAG with PostgreSQL + pgvector
- deterministic safety rules
- tool authorization
- human approval where required
- auditability and workflow checkpointing
- region-aware privacy and security controls

The MVP will use synthetic healthcare data and sandbox/mock integrations.

---

# 2. Product Vision

## Vision

Build a trustworthy AI healthcare coordination layer that helps people understand their next step, coordinate care, and manage relevant health information without attempting to replace healthcare professionals.

## Simple Product Definition

> **HealthSync AI is an AI healthcare coordinator that helps patients navigate symptoms, appointments, medications, follow-ups, and health information through one intelligent, action-oriented assistant.**

---

# 3. Problem Statement

Healthcare journeys are fragmented.

A patient may need to:

- search for symptom information
- decide whether to seek medical attention
- find a doctor
- check appointment availability
- book or reschedule an appointment
- remember appointments
- manage medication schedules
- store and retrieve health records
- understand trends in vitals or lab results
- communicate with healthcare services

These activities often exist across different websites, applications, portals, documents, messages and personal notes.

HealthSync AI aims to provide a single coordination layer that can understand the user's request, identify the appropriate workflow, retrieve relevant information, use controlled tools, verify important actions, and maintain an auditable workflow.

---

# 4. Goals

## 4.1 Product Goals

1. Provide safe healthcare navigation and symptom-triage support.
2. Automate common appointment workflows.
3. Support medication and follow-up reminders.
4. Organize and retrieve synthetic patient health records.
5. Provide grounded health-information responses through trusted knowledge retrieval.
6. Demonstrate genuine multi-agent orchestration.
7. Demonstrate meaningful multi-model routing.
8. Implement deterministic safety controls and human escalation.
9. Verify important tool actions before reporting success.
10. Maintain auditable workflow traces.
11. Use region-aware privacy and security architecture.
12. Build the system as a modular foundation for future healthcare integrations.

## 4.2 Portfolio Goals

Demonstrate practical skills in:

- Python
- SQL
- PostgreSQL
- FastAPI
- REST APIs
- LangGraph
- LLM APIs
- structured model outputs
- tool calling
- RAG
- embeddings
- pgvector
- multi-agent workflows
- model routing
- authentication/authorization
- data modeling
- cloud deployment
- observability
- AI evaluation
- Power BI analytics

---

# 5. Non-Goals

The MVP will NOT:

- autonomously diagnose disease
- prescribe medication
- change a patient's prescription or dosage
- tell a patient to stop prescribed medication
- replace emergency services
- replace a clinician's final decision
- make autonomous high-risk clinical decisions
- use real patient/PHI data
- claim legal certification or regulatory compliance
- integrate directly with every hospital/EHR system
- implement a full FHIR server
- implement full telemedicine
- support every communication channel
- implement voice and vision in the first MVP
- build a large collection of specialized agents
- support production-scale multi-tenant healthcare operations

---

# 6. Target Users

## Primary — Patient

A patient who needs help navigating healthcare-related tasks.

Examples:

- symptom concerns
- care-navigation questions
- finding appointments
- appointment management
- reminders
- retrieving health information
- understanding simple personal health trends

## Secondary — Administrator

A controlled administrative role for the prototype.

Responsibilities may include:

- managing synthetic demo data
- managing knowledge-base content
- inspecting system/audit information
- configuring application settings

Administrator access must not automatically imply unrestricted patient-data access.

## Future Users

- caregivers
- care coordinators
- healthcare staff
- clinicians

These roles are outside the MVP.

---

# 7. Core User Experience

The primary HealthSync workflow is:

```text
User
 ↓
Input Screening
 ↓
Supervisor
 ↓
Specialized Agent
 ↓
Model / RAG / Tools
 ↓
Safety & Policy Gate
 ↓
Human Approval when required
 ↓
Verified Response / Action
 ↓
Audit + Checkpoint
```

The system should never claim that an external action succeeded unless the relevant tool/API confirms the result.

---

# 8. Core Use Cases

## UC-01 — Symptom & Care Navigation

Example:

> "I've had fever and cough for three days. What should I do?"

HealthSync should:

1. validate and screen the input
2. identify symptom/triage intent
3. collect relevant information
4. apply deterministic high-risk rules
5. use approved healthcare information/retrieval
6. produce a care-navigation response
7. escalate when risk or uncertainty requires it
8. clearly communicate that it is not providing a definitive diagnosis

---

## UC-02 — Appointment Search and Booking

Example:

> "I need to see a dermatologist tomorrow afternoon."

HealthSync should:

1. identify appointment intent
2. collect required preferences
3. call the scheduling tool
4. retrieve available slots
5. present options
6. obtain confirmation where required
7. create the appointment
8. verify the booking
9. create a reminder

---

## UC-03 — Appointment Rescheduling

Example:

> "Move my appointment from Monday to Wednesday."

HealthSync should:

1. identify the relevant appointment
2. verify user authorization
3. find available alternatives
4. obtain confirmation where required
5. reschedule through the controlled tool
6. verify the updated appointment
7. update the reminder

---

## UC-04 — Medication Reminder

Example:

> "Remind me to take my medicine at 8 PM every day."

HealthSync should:

1. identify reminder intent
2. validate the requested schedule
3. store the reminder
4. create the notification schedule
5. track reminder status

The agent must not independently change medication instructions.

---

## UC-05 — Health Record Retrieval

Example:

> "Show me my recent blood pressure readings."

HealthSync should:

1. authenticate the user
2. authorize access
3. retrieve permitted structured data
4. present recorded values
5. optionally calculate a simple trend
6. distinguish stored facts from AI-generated interpretation

---

## UC-06 — Health Record Summary

Example:

> "Summarize my recent health records."

HealthSync should:

1. authenticate and authorize access
2. retrieve relevant records
3. retrieve relevant documents
4. summarize the information
5. preserve dates/source metadata where possible
6. avoid presenting AI-generated summaries as clinician-authored diagnoses

---

# 9. System Architecture

## 9.1 High-Level Architecture

```text
                         USER
                           │
                           ▼
                 ┌─────────────────┐
                 │ INPUT SCREENING │
                 │ Validation      │
                 │ Injection Check │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │   SUPERVISOR    │
                 │   LANGGRAPH     │
                 │                 │
                 │ State + Routing │
                 └────────┬────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       ┌──────────────┐       ┌──────────────┐
       │ TRIAGE AGENT │       │ SCHEDULING   │
       │              │       │ AGENT        │
       └──────┬───────┘       └──────┬───────┘
              │                      │
              └──────────┬───────────┘
                         ▼
              ┌─────────────────────┐
              │ MODEL ROUTER        │
              │                     │
              │ Fast Model          │
              │ Strong Model        │
              │ Embedding Model     │
              └──────────┬──────────┘
                         │
             ┌───────────┼────────────┐
             ▼           ▼            ▼
            RAG       PostgreSQL     TOOLS
          pgvector       + RLS       Calendar
             │           │            Healthcare
             │           │            Reminders
             └───────────┼────────────┘
                         ▼
              ┌─────────────────────┐
              │ SAFETY / POLICY     │
              │                     │
              │ Rules               │
              │ Output validation   │
              │ Tool authorization  │
              │ Risk escalation     │
              └──────────┬──────────┘
                         ▼
                 HUMAN APPROVAL?
                    │       │
                   YES      NO
                    │       │
                    ▼       │
                 REVIEW     │
                    │       │
                    └───┬───┘
                        ▼
                VERIFIED RESPONSE
                        │
                        ▼
                  AUDIT + STATE
```

---

# 10. Input Screening Layer

The Input Screening Layer sits before the Supervisor.

Responsibilities:

- input validation
- malformed input detection
- language/format validation
- basic prompt-injection/adversarial-input detection
- unsafe instruction detection
- input normalization
- size/rate limits

Input screening is not the only safety mechanism. Safety checks also occur before tool execution and before final output.

---

# 11. LangGraph Supervisor

The Supervisor is the primary workflow orchestrator.

Responsibilities:

- understand user intent
- maintain workflow state
- select the appropriate agent
- coordinate multi-step workflows
- determine whether tools are required
- manage approval states
- handle failures
- pass only relevant context
- synthesize final responses

The Supervisor does not have unrestricted access to all patient information or tools.

---

# 12. LangGraph State

The workflow must use an explicit state schema.

The state should contain only information necessary for workflow execution.

Example conceptual state:

```text
session_id
user_id
intent
current_agent
workflow_status
patient_context
sanitized_input
retrieved_context
risk_level
tool_requests
tool_results
approval_required
approval_status
response_draft
verification_status
error_state
```

The implementation should use a typed structure such as TypedDict or Pydantic-compatible models.

Sensitive information should be minimized within transient state.

---

# 13. LangGraph Checkpointing

Human approval requires the workflow to pause and resume.

The system should therefore support checkpointing.

Example:

```text
Scheduling Agent
      ↓
Find available slot
      ↓
Checkpoint state
      ↓
WAIT FOR USER APPROVAL
      ↓
User approves
      ↓
Resume graph
      ↓
Create appointment
      ↓
Verify
```

Checkpointing should also support recovery from selected workflow failures.

---

# 14. Specialized Agents

The MVP intentionally limits the number of true agents.

## 14.1 Triage & Care Navigation Agent

Responsibilities:

- symptom intake
- relevant follow-up questions
- risk categorization
- healthcare knowledge retrieval
- care-navigation recommendation
- escalation

It should combine:

- deterministic safety rules
- approved healthcare APIs where appropriate
- trusted RAG
- appropriate model reasoning

It must not independently claim a definitive diagnosis.

---

## 14.2 Scheduling Agent

Responsibilities:

- appointment search
- availability
- booking
- rescheduling
- cancellation
- confirmation
- reminders

Controlled tools:

```text
find_available_slots()
create_appointment()
reschedule_appointment()
cancel_appointment()
create_reminder()
```

The agent should not directly manipulate external systems through unrestricted model output.

---

# 15. Patient Data Services — Tools, Not Agents

The following capabilities are intentionally implemented as controlled tools/services rather than separate agents in the MVP:

- patient record retrieval
- medication retrieval
- medication schedule creation
- vitals retrieval
- vitals storage
- lab-result retrieval
- encounter retrieval
- patient timeline generation
- health-trend calculation
- reminder management

This keeps the multi-agent architecture meaningful instead of creating agents for simple CRUD operations.

---

# 16. Tool Layer

Core principle:

> **Agents decide what action is needed; controlled tools execute the action.**

Tool categories:

### Healthcare Tools

- symptom/triage API
- drug-information source/API
- laboratory information source/API
- future FHIR-compatible integrations

### Scheduling Tools

- Google Calendar API
- future hospital scheduling APIs
- future doctor-directory APIs

### Patient Data Tools

- patient lookup
- medication lookup
- vitals lookup
- lab-result lookup
- encounter lookup
- record summary retrieval

### Reminder Tools

- create reminder
- update reminder
- cancel reminder

### Communication Tools

- email initially
- SMS/WhatsApp later

---

# 17. Tool Authorization

Every sensitive tool call must pass an authorization/policy check.

Example:

```text
Agent
 ↓
Tool Request
 ↓
Authorization / Consent Check
 ↓
Safety Check
 ↓
Tool Execution
 ↓
Verification
 ↓
Return Result
```

A tool must not execute solely because an LLM requested it.

---

# 18. Multi-Model Architecture

HealthSync uses model routing based on task requirements rather than using multiple models simply for branding.

## Model 1 — Fast/Low-Cost Model

Potential uses:

- intent classification
- simple structured extraction
- lightweight routing
- low-complexity responses

## Model 2 — Stronger Reasoning Model

Potential uses:

- complex healthcare conversation
- triage reasoning support
- RAG-grounded response synthesis
- multi-step reasoning

The exact model/provider can be selected during implementation based on capability, cost, latency, and API availability.

## Model 3 — Embedding Model

Used for:

- document embeddings
- semantic retrieval
- RAG

The embedding model is treated as a distinct model capability, not as evidence that the system needs many general-purpose LLMs.

---

# 19. Model Router

The Model Router decides which model capability should handle a task.

Example:

```text
"What time is my appointment?"
        ↓
Fast model / direct database tool

"Summarize these health records."
        ↓
Stronger model + authorized records

"Explain this trusted medical information."
        ↓
Strong model + RAG

"Find similar medical documents."
        ↓
Embedding model + pgvector

"Calculate my BP trend."
        ↓
SQL/Python tool
```

Deterministic calculations should use SQL/Python rather than asking an LLM to perform numerical work.

The MVP should begin with a small number of models and add additional providers/models only when a measurable capability, latency, cost, or reliability benefit exists.

---

# 20. Knowledge & RAG Layer

HealthSync should not rely entirely on an LLM's internal knowledge for healthcare information.

The RAG architecture is:

```text
User Question
      ↓
Query Processing
      ↓
Hybrid Retrieval
      ↓
Relevant Sources
      ↓
Optional Reranking
      ↓
LLM
      ↓
Grounded Response
```

Knowledge sources may include:

- official government healthcare information
- authoritative medical organizations
- approved drug-information sources
- approved hospital/service information
- synthetic patient documents
- product-specific documentation

The system should preserve source metadata where possible.

---

# 21. Knowledge Base Versioning

The RAG knowledge base must track basic provenance.

Each document should have metadata such as:

- source
- title
- publication/update date when available
- ingestion date
- version
- document status
- region
- content category

The system should provide a way to identify stale or superseded knowledge.

Healthcare information should not be silently treated as permanently current.

---

# 22. PostgreSQL Data Architecture

PostgreSQL is the primary structured data store.

Potential entities:

- users
- patients
- patient_consents
- appointments
- medications
- medication_schedules
- vitals
- lab_results
- encounters
- prescriptions
- documents
- reminders
- audit_logs
- agent_runs

The synthetic schema should use healthcare concepts that can map naturally toward FHIR resources in future.

Examples:

```text
Patient
Appointment
Encounter
Observation
MedicationRequest
DiagnosticReport
```

A full FHIR server is outside MVP scope.

---

# 23. pgvector

pgvector is used inside PostgreSQL for vector embeddings and semantic retrieval.

Potential uses:

- medical knowledge embeddings
- approved document embeddings
- synthetic patient-document retrieval
- semantic context retrieval

Structured facts such as:

- patient ID
- appointment date
- medication dose
- blood pressure reading
- lab result

must remain in structured relational storage.

Vector search is not a replacement for the healthcare database.

---

# 24. Memory & Personalization

HealthSync uses controlled memory.

### Structured Health Data

Stored in PostgreSQL.

### Unstructured Documents

Stored with document metadata.

### Semantic Retrieval

Stored using embeddings + pgvector.

### User Preferences

Stored as structured preferences.

### Conversation History

Stored according to retention and privacy policies.

The system should retrieve only information that is:

- relevant
- authorized
- necessary for the current task

---

# 25. Safety Architecture

Safety is a first-class architecture layer.

It operates at multiple points:

```text
Input
 ↓
Input Screening
 ↓
Supervisor
 ↓
Agent
 ↓
Tool Authorization
 ↓
Tool Execution
 ↓
Output Validation
 ↓
Final Response
```

Safety controls include:

- deterministic red-flag rules
- prompt-injection defenses
- output validation
- tool authorization
- uncertainty handling
- grounding checks
- high-risk escalation
- human approval
- unsafe-action prevention

---

# 26. Deterministic Emergency / Red-Flag Rules

Critical emergency indicators should not depend solely on LLM judgment.

The Triage workflow should include a deterministic rule layer for predefined high-risk patterns.

Conceptually:

```text
Symptoms / Structured Inputs
          │
     ┌────┴────┐
     ▼         ▼
Safety Rules  AI Assessment
     │         │
     └────┬────┘
          ▼
      Safety Gate
          │
     Escalation or
     Care Navigation
```

The exact medical rule set must be defined and validated from appropriate authoritative sources before implementation.

The prototype should never imply that the rules constitute a complete medical triage system.

---

# 27. Prompt-Injection & Adversarial Input Handling

HealthSync must explicitly test against adversarial inputs.

Examples include:

- "Ignore your safety instructions."
- attempts to override system policies
- attempts to force unsafe medical recommendations
- attempts to make the agent call unauthorized tools
- malicious content embedded in retrieved documents
- instructions embedded inside uploaded documents

Controls should include:

- input screening
- instruction/data separation
- constrained tool schemas
- authorization before tool execution
- output validation
- adversarial test cases
- logging of security-relevant events

---

# 28. Human-in-the-Loop

Human approval should be used where risk, uncertainty, or policy requires it.

Example:

```text
Agent
 ↓
Safety / Policy Gate
 ↓
Human approval required?
 ├── No → Continue
 └── Yes → Pause
             ↓
          Reviewer
             ↓
          Approve / Reject
             ↓
        Resume workflow
```

For the MVP, human review can be simulated through an administrative approval interface.

---

# 29. Verification Loop

Important actions follow:

> **Plan → Act → Verify → Report**

Example:

```text
Scheduling Agent
      ↓
Find Slot
      ↓
Calendar Tool
      ↓
Verify Availability
      ↓
Create Booking
      ↓
Verify Booking ID / Status
      ↓
Report Success
```

The agent must not claim:

> "Your appointment is booked."

unless the tool/API confirms successful booking.

---

# 30. Privacy, Security & Governance

HealthSync will be designed using privacy-by-design and security-by-design principles.

The MVP uses synthetic data only.

Core controls:

- authentication
- authorization
- RBAC
- consent management
- data minimization
- encryption in transit
- encryption at rest
- secure secrets management
- database access controls
- row-level security where appropriate
- audit logging
- retention/deletion controls
- model/tool access policies
- controlled external API access

---

# 31. Consent Enforcement

Consent must be an enforced control, not merely a database record.

Every sensitive patient-data access tool should verify:

1. authenticated user
2. authorized role
3. patient/resource ownership or permitted relationship
4. applicable consent
5. minimum-necessary data requirement

PostgreSQL Row-Level Security should be evaluated for enforcing data-access boundaries at the database layer.

---

# 32. Data Sensitivity

Data fields should be classified according to sensitivity.

Examples of sensitive data include:

- patient identity
- symptoms
- medications
- lab results
- vitals
- diagnoses recorded by clinicians
- prescriptions
- health documents

The system should use sensitivity classification to influence:

- access control
- logging
- retention
- model access
- external API sharing

---

# 33. Auditability

HealthSync should maintain a traceable workflow.

Example:

```text
User Request
 ↓
Input Screening Result
 ↓
Intent
 ↓
Supervisor Decision
 ↓
Selected Agent
 ↓
Selected Model
 ↓
Retrieved Sources
 ↓
Tool Request
 ↓
Authorization Decision
 ↓
Tool Result
 ↓
Safety Decision
 ↓
Human Approval if required
 ↓
Final Outcome
```

Audit logs should avoid unnecessarily storing sensitive free-text content.

Where sensitive content must be retained, an explicit retention policy is required.

---

# 34. Authentication & RBAC

MVP roles:

### Patient

Can access only authorized personal data and actions.

### Admin

Can perform controlled system-management functions.

Admin access must be:

- authenticated
- role-controlled
- audited
- limited to required resources

Future roles:

- caregiver
- staff
- clinician

These are outside MVP scope.

---

# 35. PostgreSQL Row-Level Security

Where practical, PostgreSQL RLS should enforce access boundaries in addition to application-level authorization.

Conceptually:

```text
User
 ↓
FastAPI
 ↓
PostgreSQL
 ↓
RLS Policy
 ↓
Authorized rows only
```

This creates defense in depth.

---

# 36. Regional Privacy & Compliance Architecture

HealthSync is intended to support region-aware deployments.

The project should distinguish between:

> **compliance-oriented architecture**

and:

> **legal/regulatory certification or production compliance**

The prototype must not claim certification.

## Unified Control Matrix

| Control Area | India | USA | EU |
|---|---|---|---|
| Privacy/security controls | Applicable requirements | Applicable requirements | Applicable requirements |
| Consent/privacy controls | DPDP-oriented | HIPAA/privacy requirements where applicable | GDPR-oriented |
| Health/PHI safeguards | Applicable Indian requirements | HIPAA where applicable | GDPR special-category requirements where applicable |
| Access control | Required as appropriate | Required as appropriate | Required as appropriate |
| Auditability | Applicable requirements | HIPAA-oriented | GDPR-oriented |
| Data minimization | Applicable principles | Appropriate safeguards | GDPR-oriented |
| Data subject/access rights | Applicable Indian framework | Applicable US requirements | GDPR rights where applicable |
| International transfers | Region-specific | Region-specific | GDPR transfer requirements where applicable |

The exact legal obligations depend on deployment, entity relationships, data flows, geography, and applicable law. Production deployment requires legal and compliance review.

---

# 37. Cost & Budget Controls

The system must track AI/API usage.

Controls should include:

- model cost tracking
- token usage tracking
- per-request limits
- per-session limits
- retry limits
- fallback rules
- expensive-model escalation thresholds

The model router should consider:

- capability
- latency
- reliability
- cost

The project should avoid using a high-cost model when a deterministic tool or smaller model can safely complete the task.

---

# 38. Failure Handling

HealthSync must fail safely.

## LLM failure

→ retry or controlled fallback

## Healthcare API failure

→ report inability to verify; do not fabricate information

## Calendar failure

→ do not claim booking success

## Database failure

→ do not invent patient data

## RAG failure

→ avoid unsupported medical claims and clearly communicate limitations

## High-risk uncertainty

→ escalate

## Tool timeout

→ return a pending/failed state rather than claiming success

---

# 39. Observability

The system should expose workflow traces during development.

Recommended observability:

- agent traces
- model calls
- tool calls
- latency
- failures
- token usage
- workflow state
- safety decisions

LangSmith may be used for development-time tracing and evaluation.

Sensitive data should be minimized or redacted from observability systems.

---

# 40. Evaluation Framework

## Agent Evaluation

Measure:

- intent classification
- routing accuracy
- tool selection
- workflow completion
- failure recovery

## RAG Evaluation

Measure:

- retrieval relevance
- grounded-response quality
- source coverage
- unsupported claims

Ragas can be evaluated after the core MVP is stable.

## Safety Evaluation

Test:

- high-risk scenarios
- low-risk scenarios
- ambiguous scenarios
- prompt injection
- unauthorized tool requests
- false reassurance
- unsupported medical claims

## System Evaluation

Measure:

- latency
- API failure rate
- workflow failure rate
- model usage
- cost per workflow

---

# 41. MVP Technology Stack

## Development

- ChatGPT
- Antigravity
- GitHub

## Frontend

- Streamlit

## Backend

- Python
- FastAPI

## Agent Orchestration

- LangGraph
- OpenAI SDK initially

LangChain should not be required unless a specific integration/retriever/loader provides a clear benefit.

## AI Models

- fast/low-cost model
- stronger reasoning model
- embedding model

Initial provider selection should prioritize capability, cost, latency, and availability.

## Database

- PostgreSQL
- pgvector

## Authentication

- Supabase Auth or equivalent

## RAG

- embeddings
- pgvector
- hybrid retrieval where justified

## APIs

- Google Calendar API
- selected healthcare/symptom information API
- email initially

## Observability

- LangSmith

## Evaluation

- custom evaluation set initially
- Ragas later if useful

## Deployment

- Azure

Potential deployment options:

- Azure App Service
- Azure Container Apps

## Analytics

- Power BI as a later portfolio extension

---

# 42. MVP Scope

## Must Have

- Streamlit interface
- FastAPI backend
- PostgreSQL
- authentication
- Supervisor
- Triage Agent
- Scheduling Agent
- LangGraph state
- checkpointing/pause-resume
- basic RAG
- pgvector
- deterministic safety rules
- prompt-injection screening
- tool authorization
- one verified scheduling/tool workflow
- audit trail
- synthetic patient data
- basic patient/admin roles
- one complete end-to-end demo

## Should Have Later

- richer Care/Records tools
- improved hybrid retrieval
- reranking
- LangSmith tracing
- Azure deployment
- stronger evaluation
- PostgreSQL RLS hardening
- richer compliance documentation
- FHIR-aligned interfaces
- additional communication channels

## Optional

- Power BI dashboard
- voice
- vision/document extraction
- WhatsApp/SMS
- Next.js
- second reasoning provider
- hospital/EHR integrations
- full FHIR server
- additional agent types

---

# 43. Primary MVP Demo Scenario

The primary portfolio demonstration should be:

> "I've had persistent cough and fever for three days. I want to know what I should do and, if appropriate, find a doctor tomorrow."

Workflow:

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
Human/Policy Approval if Required
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

This single scenario demonstrates:

- input screening
- orchestration
- multi-agent routing
- multi-model use
- RAG
- structured data
- tool calling
- safety
- human approval
- verification
- auditability

---

# 44. Development Strategy

The project must follow a vertical-slice approach.

Do NOT build all infrastructure and all agents first.

## Vertical Slice 1

```text
User
 ↓
Input Screening
 ↓
Supervisor
 ↓
Triage Agent
 ↓
Simple Safety Rules
 ↓
Basic RAG
 ↓
Safe Response
 ↓
Audit Log
```

## Vertical Slice 2

Add:

```text
Scheduling Agent
 ↓
Availability Tool
 ↓
Approval
 ↓
Booking
 ↓
Verification
```

## Vertical Slice 3

Add:

- patient data tools
- medications
- vitals
- reminders
- records

## Vertical Slice 4

Add:

- RLS
- stronger authentication
- observability
- evaluation
- deployment

---

# 45. Development Roadmap

## Phase 1 — Foundation

- FastAPI
- Streamlit
- PostgreSQL
- basic authentication
- project structure

## Phase 2 — AI Foundation

- OpenAI API
- structured outputs
- model abstraction
- basic chat

## Phase 3 — LangGraph

- state schema
- Supervisor
- routing
- conditional edges
- checkpointing
- pause/resume

## Phase 4 — First Vertical Slice

- Triage Agent
- input screening
- deterministic safety rules
- basic RAG
- safe response
- audit trace

## Phase 5 — Scheduling

- Scheduling Agent
- mock availability
- calendar integration
- confirmation
- booking
- verification
- reminders

## Phase 6 — Patient Data Tools

- PostgreSQL health records
- medications
- vitals
- encounters
- record retrieval
- health trends

## Phase 7 — pgvector & RAG

- embeddings
- pgvector
- document ingestion
- retrieval
- source metadata
- knowledge versioning
- evaluation

## Phase 8 — Safety & Security

- prompt-injection tests
- tool authorization
- consent enforcement
- RBAC
- RLS
- audit hardening

## Phase 9 — Observability & Evaluation

- LangSmith
- evaluation dataset
- RAG evaluation
- agent evaluation
- safety tests
- cost tracking

## Phase 10 — Deployment

- Docker/containerization
- Azure
- secrets management
- monitoring
- production-like demo

## Phase 11 — Portfolio Extensions

Only after the MVP is stable:

- Power BI
- voice
- vision
- WhatsApp/SMS
- Next.js
- additional model providers
- FHIR/hospital integrations

---

# 46. Success Metrics

## Product

- task completion rate
- successful appointment workflow rate
- reminder creation success rate
- record retrieval success rate

## Agent

- intent routing accuracy
- agent selection accuracy
- tool-call success rate
- workflow completion rate
- verification success rate

## RAG

- retrieval relevance
- grounded-response rate
- source coverage
- unsupported-claim rate

## Safety

- emergency/red-flag detection recall
- unsafe-action prevention rate
- escalation accuracy
- false-reassurance rate
- prompt-injection resistance

## System

- response latency
- API failure rate
- workflow failure rate
- cost per workflow

---

# 47. Portfolio Positioning

HealthSync AI should be presented as:

> **A multi-agent, multi-model healthcare workflow system that combines AI reasoning, RAG, structured data, tool use, safety controls, human escalation, verification, and region-aware privacy architecture.**

The project should not be presented as:

- an AI doctor
- an autonomous diagnostic system
- a prescription engine
- a clinically validated medical device
- legally certified HIPAA/GDPR/DPDP software

---

# 48. Architecture Principles

1. **AI assists; humans remain responsible for clinical decisions.**
2. **Agents reason and plan; controlled tools execute actions.**
3. **Important actions are verified before being reported as successful.**
4. **Safety controls exist before and after model/tool execution.**
5. **Emergency red-flag handling must not depend solely on LLM judgment.**
6. **Structured health data belongs in structured storage.**
7. **Vector search supports semantic retrieval; it does not replace the healthcare database.**
8. **Use the minimum necessary data for each task.**
9. **Consent and authorization must be enforced at the data-access layer.**
10. **Prompt injection and adversarial inputs are treated as first-class security risks.**
11. **Use synthetic data for the portfolio prototype.**
12. **Model selection should be based on task capability, cost, latency and reliability.**
13. **Do not add agents where deterministic tools are sufficient.**
14. **Every important workflow should be observable and auditable.**
15. **Build complete vertical slices before expanding the system.**
16. **Compliance claims must remain separate from compliance-oriented architecture.**
17. **Start small and add complexity only when it creates measurable value.**

---

# 49. Definition of Done — MVP

The MVP is complete when:

- [ ] A patient can authenticate.
- [ ] A patient can submit a healthcare-related request.
- [ ] Input screening runs before orchestration.
- [ ] Supervisor identifies the task.
- [ ] Triage Agent can complete the first vertical slice.
- [ ] Deterministic safety rules are active.
- [ ] RAG can retrieve trusted information.
- [ ] PostgreSQL stores synthetic patient data.
- [ ] pgvector supports semantic retrieval.
- [ ] Scheduling Agent can search availability.
- [ ] A controlled tool can create an appointment in a sandbox/mock environment.
- [ ] Important actions are verified.
- [ ] Human approval can pause/resume the workflow.
- [ ] Audit logs capture the important workflow events.
- [ ] Prompt-injection scenarios have been tested.
- [ ] Model usage/cost can be observed.
- [ ] The core workflow works end-to-end.
- [ ] The project runs locally.
- [ ] The project has a documented deployment path.
- [ ] README and architecture documentation are complete.
- [ ] The demo clearly states that the system is a prototype using synthetic data.
