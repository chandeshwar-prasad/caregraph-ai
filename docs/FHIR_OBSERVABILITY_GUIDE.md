# 🏥 CareGraph AI — FHIR R4 Interoperability & Observability Guide

> **Enterprise EHR Interoperability (HL7 FHIR R4) & Production-Grade Observability (Prometheus + Grafana)**

---

## 📌 Table of Contents
1. [Architectural Overview](#architectural-overview)
2. [HL7 FHIR R4 Interoperability Layer](#hl7-fhir-r4-interoperability-layer)
   - [Supported Resources & LOINC Mappings](#supported-resources--loinc-mappings)
   - [Connecting to Sandbox / Live EHR](#connecting-to-sandbox--live-ehr)
   - [Deterministic Offline / Fallback Mode](#deterministic-offline--fallback-mode)
3. [Zero-PHI Observability Architecture](#zero-phi-observability-architecture)
   - [Prometheus Metrics Catalog](#prometheus-metrics-catalog)
   - [Scraping `/metrics`](#scraping-metrics)
   - [Grafana Pre-Provisioned Dashboards](#grafana-pre-provisioned-dashboards)
4. [Quickstart: Running with Docker Compose](#quickstart-running-with-docker-compose)
5. [Live Demo Walkthrough Scenarios](#live-demo-walkthrough-scenarios)

---

## 🏗️ Architectural Overview

CareGraph AI integrates HL7 FHIR R4 clinical systems while maintaining strict zero-trust security gates and real-time observability:

```
                  ┌──────────────────────────────────────────────┐
                  │           User / Web Client / API           │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │    Server-Side Authorization & Consent Gate   │
                  │        (authorize_tool + Zero IDOR)          │
                  └──────────────────────┬───────────────────────┘
                                         │
                      ┌──────────────────┴──────────────────┐
                      ▼                                     ▼
      ┌───────────────────────────────┐     ┌───────────────────────────────┐
      │   Local Encrypted Database    │     │   HL7 FHIR R4 Gateway         │
      │   (PostgreSQL + pgvector)     │     │   (SMART on FHIR / EHRs)      │
      └───────────────┬───────────────┘     └───────────────┬───────────────┘
                      │                                     │
                      └──────────────────┬──────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       Zero-PHI Telemetry Bridge (Scrubber)    │
                  └──────────────────────┬───────────────────────┘
                                         │
                      ┌──────────────────┴──────────────────┐
                      ▼                                     ▼
      ┌───────────────────────────────┐     ┌───────────────────────────────┐
      │    Prometheus Server (:9090)  │     │   Grafana Dashboard (:3000)   │
      │    (Scrapes /metrics)         │     │   (Pre-configured Panels)     │
      └───────────────────────────────┘     └───────────────────────────────┘
```

---

## 🩺 HL7 FHIR R4 Interoperability Layer

The FHIR layer enables bidirectional exchange between CareGraph AI's domain models and external electronic health record (EHR) systems.

### Supported Resources & LOINC Mappings

| Domain Concept | FHIR Resource | Fields Extracted / Mapped |
| :--- | :--- | :--- |
| **Patient Profile** | `Patient` | `name` (given, family), `birthDate`, `gender`, `telecom` (email, phone) |
| **Medications** | `MedicationRequest` / `MedicationStatement` | `medicationCodeableConcept`, `dosageInstruction`, `timing`, `doseAndRate`, `note` |
| **Blood Pressure** | `Observation` (LOINC `85354-9` / `8480-6` / `8462-4`) | Systolic / Diastolic compound quantities (`mmHg`) |
| **Heart Rate** | `Observation` (LOINC `8867-4`) | Value quantity (`bpm`) |
| **Body Weight** | `Observation` (LOINC `29463-7`) | Value quantity (`kg` or `lbs`) |
| **Body Temp** | `Observation` (LOINC `8310-5`) | Value quantity (`Cel` or `degF`) |
| **Oxygen (SpO2)** | `Observation` (LOINC `2708-6` / `59408-5`) | Percentage saturation (`%`) |
| **Appointment Booking** | `Appointment` | `participant` (Practitioner, Patient), `start`, `status`, `description` |

### Connecting to Sandbox / Live EHR

Set the following environment variables in `.env`:

```bash
# FHIR Gateway Configuration
FHIR_SERVER_URL=https://r4.smarthealthit.org
FHIR_SANDBOX_MODE=true
FHIR_MOCK_FALLBACK=true

# For authenticated EHRs (SMART on FHIR OAuth2):
FHIR_CLIENT_ID=your_smart_client_id
FHIR_CLIENT_SECRET=your_smart_client_secret
FHIR_ACCESS_TOKEN=optional_bearer_token
```

### Deterministic Offline / Fallback Mode
When `FHIR_MOCK_FALLBACK=true`, if the remote FHIR server is unreachable or offline, the client automatically falls back to rich synthetic FHIR resources for demo patients (e.g. `SmartChris`, `patient-101`), guaranteeing 100% test reliability.

---

## 📊 Zero-PHI Observability Architecture

### Prometheus Metrics Catalog

All metrics emitted by CareGraph AI strictly exclude Patient Health Information (PHI):

| Metric Name | Type | Description / Labels |
| :--- | :--- | :--- |
| `caregraph_graph_node_executions_total` | Counter | Node throughput (`node_name`, `status`) |
| `caregraph_graph_node_latency_seconds` | Histogram | Latency distribution per graph node |
| `caregraph_intent_classifications_total` | Counter | Intent classifications (`detected_intent`, `match`) |
| `caregraph_safety_escalations_total` | Counter | Red-flag and emergency triggers (`escalation_type`, `risk_level`) |
| `caregraph_tool_executions_total` | Counter | Tool authorization outcomes (`tool_name`, `status`) |
| `caregraph_fhir_api_calls_total` | Counter | FHIR transactions (`method`, `resource_type`, `status`) |
| `caregraph_fhir_api_latency_seconds` | Histogram | Network roundtrip latency to EHR server |
| `caregraph_llm_token_usage_total` | Histogram | Token consumption (`model`, `token_type`) |
| `caregraph_estimated_total_cost_usd` | Gauge | Cumulative AI financial expenditure in USD |
| `caregraph_active_sessions_current` | Gauge | Active concurrent user sessions |

### Scraping `/metrics`

The backend exposes standard Prometheus text output:
```bash
curl http://localhost:8000/metrics
```

Example output snippet:
```text
# HELP caregraph_graph_node_executions_total Total executions of graph nodes categorized by status
# TYPE caregraph_graph_node_executions_total counter
caregraph_graph_node_executions_total{node_name="triage",status="success"} 42.0
caregraph_graph_node_executions_total{node_name="records",status="success"} 18.0

# HELP caregraph_estimated_total_cost_usd Cumulative estimated LLM inference costs in USD
# TYPE caregraph_estimated_total_cost_usd gauge
caregraph_estimated_total_cost_usd 0.003418
```

### Grafana Pre-Provisioned Dashboards
Grafana is pre-configured with the **CareGraph AI Production Dashboard** featuring:
* Real-time p95/p50 latency curves by agent node.
* Safety & emergency escalation spikes.
* Live FHIR query throughput and EHR latency.
* Financial token costs ($ USD) and model tier distribution.

---

## 🚀 Quickstart: Running with Docker Compose

To start the full CareGraph AI stack (API + Database + Frontend + Prometheus + Grafana):

```bash
docker compose up --build -d
```

### Port Map:
* **CareGraph API**: `http://localhost:8000` (Docs: `http://localhost:8000/docs`, Metrics: `http://localhost:8000/metrics`)
* **CareGraph UI**: `http://localhost:8501`
* **Prometheus**: `http://localhost:9090`
* **Grafana**: `http://localhost:3000` (User: `admin`, Password: `admin`)

---

## 🎬 Live Demo Walkthrough Scenarios

### Scenario 1: FHIR Medication Lookup
1. Log in to CareGraph AI.
2. Send message: `"Show me my active medications"`. Pass `"use_fhir": true, "fhir_patient_id": "SmartChris"`.
3. Agent queries FHIR server, parses `MedicationRequest` resources, and responds with dosage and instructions with `[Source: HL7 FHIR R4 Interoperability Gateway]`.
4. Check Grafana (`http://localhost:3000`): Observe spike in `caregraph_fhir_api_calls_total` and node latency.

### Scenario 2: Safety Escalation Real-time Metric
1. Send message: `"I have severe crushing chest pain and difficulty breathing"`.
2. Deterministic safety screener triggers emergency escalation without invoking LLM.
3. Check Prometheus (`http://localhost:9090`): `caregraph_safety_escalations_total{risk_level="emergency"}` increments immediately.

### Scenario 3: HITL Scheduling with FHIR EHR Synchronization
1. Send message: `"Book an appointment with a cardiologist tomorrow"`.
2. Human-in-the-loop interrupt prompts for confirmation.
3. Upon approval (`/chat/approve`), the agent persists the booking locally and creates an HL7 FHIR R4 `Appointment` resource returning the FHIR Resource ID.
