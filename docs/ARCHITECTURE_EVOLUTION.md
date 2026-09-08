# CareGraph AI — Architectural Evolution

## From Multi-Interface Application to Stateful Multimodal Healthcare Workflow

CareGraph AI evolved from a LangGraph-based care-coordination application with separate voice, vision, and messaging interfaces into a more integrated healthcare AI workflow.

The key architectural improvement is **not the addition of more AI features**. It is the movement of previously isolated interfaces and external capabilities into a shared, stateful workflow with explicit safety, authorization, consent, interoperability, human approval, and observability boundaries.

---

## 1. Architectural Evolution

### Earlier architecture

The initial implementation exposed separate modality endpoints:

```text
Voice  ──> STT ──> response
Vision ──> analysis ──> response
Chat   ──> LangGraph workflow
SMS    ──> messaging utility
```

This provided multiple interfaces, but the modalities were not all participating in the same reasoning and workflow state.

### Current architecture

The evolved architecture normalizes multimodal inputs into the same LangGraph execution path:

```text
                 ┌───────────────┐
                 │   Text Chat   │
                 └───────┬───────┘
                         │
                 ┌───────▼───────┐
                 │ Voice / STT   │
                 └───────┬───────┘
                         │
                 ┌───────▼───────┐
                 │ Vision / Docs │
                 └───────┬───────┘
                         │
                         ▼
                ┌──────────────────┐
                │  CareGraph State │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ LangGraph Router │
                └────────┬─────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Triage         Records       Scheduling
          │              │              │
          └──────────────┼──────────────┘
                         ▼
              Safety / Authorization
                         │
                    Patient Consent
                         │
                         ▼
                 Human Approval
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
          FHIR / EHR               SMS

                 ┌────────────────┐
                 │ Observability  │
                 │ Prometheus /   │
                 │ Grafana        │
                 └────────────────┘
```

The architectural distinction is therefore:

> **Multimodality is now an input capability of the workflow rather than a collection of disconnected interface features.**

---

## 2. Architectural Principles

### Shared workflow state

Text, voice transcription, and visual/document observations are normalized into the same care-coordination execution path rather than being handled as independent utility workflows.

### LLM proposes; deterministic systems enforce

The LLM is used for interpretation and routing. It is not the final authority for safety, access control, consent, or consequential external actions.

```text
LLM
 │
 ├── interpret
 ├── classify
 └── route

Deterministic application layer
 │
 ├── safety checks
 ├── authorization
 ├── consent
 ├── validation
 └── external-action controls
```

### Human approval for consequential actions

Appointment scheduling remains Human-in-the-Loop. The workflow can identify and prepare an action, but the consequential booking step requires explicit patient approval.

### Interoperability through an adapter boundary

FHIR access is isolated behind a dedicated client/adapter layer so the workflow does not need to embed EHR-specific HTTP details throughout the graph.

### Observability without intentionally exporting PHI

Operational metrics focus on workflow behavior — latency, node executions, safety escalations, LLM usage, costs, tools, and FHIR transactions — rather than patient free text.

---

## 3. Healthcare Interoperability Layer

CareGraph includes an HL7 FHIR R4 client/adapter layer with support for sandbox-oriented FHIR workflows, caching, retry handling, and deterministic mock fallback behavior.

FHIR operations are integrated with the workflow rather than exposed as an unrelated API utility. Patient-data and scheduling workflows can use FHIR operations while remaining subject to application-level authorization and consent controls.

The architecture is intentionally described as **FHIR R4 interoperability support**, not as a production EHR certification or universal Epic/Cerner integration.

---

## 4. Safety and Governance Boundaries

CareGraph separates model reasoning from safety-critical application controls.

```text
Patient input
     │
     ▼
Deterministic red-flag screening
     │
     ▼
LLM interpretation / routing
     │
     ▼
Server-side authorization
     │
     ▼
Patient consent
     │
     ▼
Human approval when required
     │
     ▼
External action
```

This architecture is particularly important in healthcare because an LLM should not be treated as the access-control, consent, or emergency-safety authority.

---

## 5. Production Observability

The observability layer exposes Prometheus-compatible metrics for:

- graph node execution
- workflow latency
- intent routing
- safety escalations
- tool execution outcomes
- LLM token usage and request latency
- estimated model cost
- FHIR API calls and latency
- active workflow sessions

These metrics support operational visibility without turning application telemetry into a repository for clinical conversation content.

This should be described as **LLM/application observability or LLMOps-oriented production telemetry**, rather than as a complete MLOps platform.

---

## 6. Multimodal Workflow

### Voice

```text
Audio
  ↓
In-memory speech transcription
  ↓
CareGraph workflow
  ↓
Clinical care-navigation response
  ↓
Optional TTS
```

### Clinical document / image

```text
Image / document
  ↓
Vision extraction
  ↓
Observation/context normalization
  ↓
CareGraph workflow
  ↓
Triage / records / care navigation
```

### Downstream action

```text
Scheduling request
  ↓
Available slot
  ↓
Human approval
  ↓
Appointment action
  ↓
Outbound confirmation
```

The important architectural property is that the modality-specific processing feeds the shared workflow rather than terminating at the interface boundary.

---

## 7. Correct Technical Positioning

### Recommended

> **CareGraph AI is a stateful multimodal clinical care-navigation and scheduling workflow orchestrated with LangGraph, integrating voice and document inputs, controlled FHIR interoperability, Human-in-the-Loop approval, and PHI-minimizing production observability.**

### Short version

> **Stateful multimodal healthcare workflow with LangGraph, FHIR interoperability, HITL approval, and production observability.**

### Avoid

- Autonomous multi-agent healthcare system
- Fully autonomous clinical agent
- HIPAA-compliant healthcare AI
- Complete healthcare MLOps platform
- Universal Epic/Cerner integration
- Production clinical decision-support system

These descriptions either overstate the architecture or imply compliance/certification that the project does not claim.

---

## 8. Portfolio Narrative

The strongest portfolio story is the architectural lesson:

> **Adding voice, vision, and messaging does not automatically make an AI application multimodal or agentic. The architecture becomes meaningfully multimodal when those modalities participate in the same stateful reasoning and action workflow.**

CareGraph's evolution demonstrates this progression:

```text
Multiple interfaces
        ↓
Shared stateful workflow
        ↓
Safety + authorization + consent boundaries
        ↓
FHIR interoperability
        ↓
Human approval for consequential actions
        ↓
Observable production workflow
```

This framing emphasizes engineering judgment and architectural maturity rather than simply counting AI features.

---

## 9. Resume Positioning

**CareGraph AI — Multimodal Clinical Care Navigation & Scheduling Workflow**

- Architected a stateful LangGraph healthcare workflow that normalizes text, voice, and clinical-document inputs into shared care-navigation, triage, records, and scheduling workflows.
- Integrated HL7 FHIR R4 interoperability behind an adapter layer with server-side authorization and patient-consent gates for controlled clinical data operations.
- Implemented Human-in-the-Loop appointment approval and downstream workflow actions, including automated appointment confirmation.
- Built Prometheus/Grafana-oriented production observability for workflow latency, safety escalations, LLM usage/cost, tool execution, and FHIR transactions with PHI-minimizing telemetry.
- Kept safety-critical controls deterministic and outside LLM authority, including red-flag escalation, authorization, consent, and consequential-action approval.

---

## 10. Scope and Compliance Disclaimer

CareGraph AI is a portfolio/research demonstration. It is designed with healthcare safety, authorization, consent, interoperability, and PHI-minimization considerations, but it is **not a formally certified or audited HIPAA-compliant system, not a medical device, and not intended for autonomous diagnosis or treatment decisions**.

FHIR sandbox/mock behavior should not be represented as production connectivity to a hospital EHR unless an actual authorized production integration exists.
