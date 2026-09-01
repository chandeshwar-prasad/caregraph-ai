# CareGraph AI — Power BI Integration Guide
## Zero-PHI Executive & Operational Analytics Architecture

This document provides a comprehensive integration guide for connecting **Microsoft Power BI** (Desktop and Service) to **CareGraph AI**. It outlines architecture, API specifications, authentication patterns, Power Query (M) ingestion recipes, zero-PHI privacy safeguards, and production deployment considerations.

---

## 1. Executive Summary & Architecture

CareGraph AI provides dedicated, server-side analytics endpoints designed for business intelligence, clinical operations oversight, agent performance monitoring, and LLM financial cost accounting.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Power BI Desktop / Service                    │
│                                                                        │
│   ┌─────────────────────┐  ┌──────────────────┐  ┌────────────────┐   │
│   │ Clinical Operations │  │ Agent Telemetry  │  │ Cost & Routing │   │
│   │     Dashboard       │  │    Dashboard     │  │   Analytics    │   │
│   └──────────┬──────────┘  └────────┬─────────┘  └────────┬───────┘   │
└──────────────┼──────────────────────┼─────────────────────┼────────────┘
               │                      │                     │
               ▼                      ▼                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│               CareGraph AI FastAPI Backend (/analytics/*)              │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Security Layer: JWT Authentication & Admin RBAC Enforcement    │   │
│   └────────────────────────────────┬───────────────────────────────┘   │
│                                    ▼                                   │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Server-Side Analytics Service (`app/services/analytics.py`)    │   │
│   │  • Strict Zero-PHI Aggregations                                │   │
│   │  • Deterministic Scrubber & Token Scrubbing                    │   │
│   │  • Tabular Export Generators (JSON / CSV)                      │   │
│   └───────┬────────────────────────┬────────────────────────┬──────┘   │
└───────────┼────────────────────────┼────────────────────────┼──────────┘
            ▼                        ▼                        ▼
┌───────────────────────┐ ┌────────────────────┐ ┌───────────────────────┐
│ SQL Clinical Database │ │ In-Memory Telemetry│ │ Token Cost Tracker    │
│ (PostgreSQL / SQLite) │ │ Buffer (Traces)    │ │ & Model Router Matrix │
└───────────────────────┘ └────────────────────┘ └───────────────────────┘
```

### Key Architectural Invariants:
1. **Server-Side Aggregation**: Calculations (e.g., medication counts, appointment distributions, error rates, model costs) occur exclusively server-side.
2. **Zero-PHI Guarantee**: Individual patient identifiers, patient names, dates of birth, contact details (email/phone), addresses, and free-text clinical notes are **never** returned by analytics endpoints.
3. **Admin RBAC Enforcement**: All analytics endpoints require authenticated users with the `admin` role. Unauthorized requests yield HTTP `401` or `403`.
4. **Decoupled LLM Authority**: The LLM agent has no authority or visibility over the analytics authorization and aggregation layer.

---

## 2. Available Datasets and Endpoints

### 2.1 Aggregated Analytics Endpoints

| Endpoint | Method | Response Model | Description |
| :--- | :--- | :--- | :--- |
| `/analytics/clinical-operations` | `GET` | `ClinicalOperationsAnalyticsResponse` | Aggregated counts of patients, appointments by status/specialty/doctor, medications by name/frequency, vitals by type, and consent status. |
| `/analytics/agent-telemetry` | `GET` | `AgentTelemetryAnalyticsResponse` | Operational performance metrics: total invocations, average latency (ms), safety escalations, error rates, intent breakdowns, and agent routing breakdowns. |
| `/analytics/cost-intelligence` | `GET` | `CostIntelligenceAnalyticsResponse` | Financial and token accounting: cumulative prompt/completion tokens, total USD cost, cost-per-workflow, model tier distribution, and pricing reference table. |

### 2.2 Tabular Export Endpoint

| Endpoint | Method | Formats | Description |
| :--- | :--- | :--- | :--- |
| `/analytics/export/{dataset_name}` | `GET` | `json`, `csv` | Returns flat, tabular records suitable for direct Power Query ingestion without complex JSON expansion. |

#### Supported `dataset_name` Values:
- `clinical-operations` (or `clinical_operations`, `clinical_summary`): Flattened metric rows across clinical domains.
- `appointments`: De-identified appointment records (ID, doctor name, specialty, appointment time, status, created at).
- `medications`: De-identified medication catalog and usage records (ID, medication name, dosage, frequency, active status, created at).
- `vitals`: De-identified vitals entries (ID, vital type, unit, recorded at, source, created at).
- `consents`: De-identified consent entries (ID, consent type, status, version, granted at, expires at).
- `agent-telemetry` (or `telemetry`): De-identified workflow execution traces (event ID, timestamp, actor role, intent, agent, latency, status, safety flag, tool name, token counts).
- `cost-intelligence` (or `costs`): De-identified workflow cost records (record ID, timestamp, workflow name, model, tokens, USD cost).

---

## 3. Authentication & Change-Control Considerations

### 3.1 Authentication Workflow

CareGraph AI authenticates users via OAuth2 Bearer Tokens (JWT).

- **Token URL**: `POST /auth/login`
- **Request Body**: `application/x-www-form-urlencoded` (`username`, `password`)
- **Required Role**: `admin` (e.g., `admin_demo` / `admin_pass`)

### 3.2 Demo vs. Production Authentication Architecture

> [!IMPORTANT]
> **Power BI Web Connector Limitation**: Standard Power BI Desktop and Power BI Service scheduled refresh with the built-in `Web.Contents` connector cannot natively execute multi-step interactive OAuth login scripts against custom `/auth/login` endpoints without a custom data connector (`.mez` file) or an API Gateway.

#### Development / Demo Environment Approach:
1. Generate an Admin JWT by sending a `POST /auth/login` request (via Swagger UI at `http://localhost:8000/docs`, cURL, or Postman):
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin_demo&password=admin_pass"
   ```
2. In Power BI Desktop, define a Power Query Parameter named `ApiToken` (or `AuthToken`) containing the Bearer token string.
3. Pass `[Headers=[#"Authorization"="Bearer " & ApiToken]]` in Power Query `Web.Contents` calls.

#### Production Enterprise Architecture:
For automated enterprise scheduled refreshes in Power BI Service:
- **Microsoft Entra ID (Azure AD)**: Configure FastAPI to accept Azure AD OAuth2 tokens using Microsoft Identity platform.
- **Azure API Management (APIM)**: Place an APIM gateway in front of CareGraph AI with managed identity authentication and token validation policies.
- **DirectLake / Fabric Data Pipeline**: Ingest tabular analytics into Azure Data Lake Storage (ADLS Gen2) or Microsoft Fabric Lakehouse via secure ETL/ELT pipelines, allowing Power BI to query Delta tables directly without storing ephemeral tokens in PBIX files.

---

## 4. Power BI Desktop Connection Guide

### Step 1: Create Parameters in Power BI Desktop
1. Open **Power BI Desktop**.
2. Click **Transform Data** to open the **Power Query Editor**.
3. In the Home ribbon, click **Manage Parameters** > **New Parameter**:
   - **Name**: `BaseUrl`
   - **Type**: `Text`
   - **Current Value**: `http://localhost:8000` (or `http://backend:8000`)
4. Create a second parameter:
   - **Name**: `AuthToken`
   - **Type**: `Text`
   - **Current Value**: `<YOUR_ADMIN_JWT_TOKEN>`

---

### Step 2: Ingest Datasets Using Power Query (M)

#### Ingestion Option A: Direct Tabular JSON Export (Recommended)

1. In Power Query Editor, click **New Source** > **Blank Query**.
2. Open **Advanced Editor** and paste the following M query for **Clinical Appointments**:

```powerquery
let
    Source = Json.Document(
        Web.Contents(
            BaseUrl & "/analytics/export/appointments?format=json",
            [
                Headers = [
                    #"Authorization" = "Bearer " & AuthToken,
                    #"Accept" = "application/json"
                ]
            ]
        )
    ),
    #"Converted to Table" = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Expanded Column1" = Table.ExpandRecordColumn(
        #"Converted to Table",
        "Column1",
        {"appointment_id", "doctor_name", "specialty", "appointment_time", "status", "created_at"},
        {"appointment_id", "doctor_name", "specialty", "appointment_time", "status", "created_at"}
    ),
    #"Changed Type" = Table.TransformColumnTypes(#"Expanded Column1", {
        {"appointment_id", Int64.Type},
        {"doctor_name", type text},
        {"specialty", type text},
        {"appointment_time", type text},
        {"status", type text},
        {"created_at", type datetime}
    })
in
    #"Changed Type"
```

#### Ingestion Option B: Direct CSV Export

For **Agent Telemetry**:

```powerquery
let
    Source = Csv.Document(
        Web.Contents(
            BaseUrl & "/analytics/export/agent-telemetry?format=csv",
            [
                Headers = [
                    #"Authorization" = "Bearer " & AuthToken
                ]
            ]
        ),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {
        {"event_id", Int64.Type},
        {"timestamp", type datetimezone},
        {"actor_role", type text},
        {"intent", type text},
        {"selected_agent", type text},
        {"latency_ms", type number},
        {"status", type text},
        {"safety_escalated", type logical},
        {"tool_name", type text},
        {"prompt_tokens", Int64.Type},
        {"completion_tokens", Int64.Type},
        {"total_tokens", Int64.Type}
    })
in
    #"Changed Type"
```

#### Ingestion Option C: Cost Intelligence Aggregates

For **LLM Token & Financial Intelligence**:

```powerquery
let
    Source = Json.Document(
        Web.Contents(
            BaseUrl & "/analytics/cost-intelligence",
            [
                Headers = [
                    #"Authorization" = "Bearer " & AuthToken,
                    #"Accept" = "application/json"
                ]
            ]
        )
    ),
    #"Extracted ModelUsage" = Source[model_usage],
    #"Converted to Table" = Record.ToTable(#"Extracted ModelUsage"),
    #"Expanded Value" = Table.ExpandRecordColumn(
        #"Converted to Table",
        "Value",
        {"invocations", "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd"},
        {"invocations", "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd"}
    ),
    #"Renamed Columns" = Table.RenameColumns(#"Expanded Value", {{"Name", "model_name"}}),
    #"Changed Type" = Table.TransformColumnTypes(#"Renamed Columns", {
        {"model_name", type text},
        {"invocations", Int64.Type},
        {"prompt_tokens", Int64.Type},
        {"completion_tokens", Int64.Type},
        {"total_tokens", Int64.Type},
        {"cost_usd", type number}
    })
in
    #"Changed Type"
```

---

## 5. Zero-PHI Privacy & Security Validation

CareGraph AI follows a HIPAA-aligned design (not a formally certified or audited HIPAA-compliant system) and Privacy by Design standards:

1. **Identifier Excision**:
   - `first_name`, `last_name`, `email`, `phone`, `date_of_birth`, and `user_id` are completely excluded from all analytics tables.
   - Surrogate keys (such as `appointment_id`, `event_id`) contain no encoded patient identifiers.
2. **Clinical Notes Exclusion**:
   - `notes` columns containing unstructured clinical free-text are omitted from analytics datasets to prevent accidental leakage of sensitive health details.
3. **Role Validation (RBAC)**:
   - Non-admin tokens (e.g., patient role) receiving a request on `/analytics/*` immediately receive an HTTP `403 Forbidden`.
   - Unauthenticated requests receive an HTTP `401 Unauthorized`.
4. **Secret Isolation**:
   - No database connection strings, API keys, or master encryption keys are exposed to the Power BI client.

---

## 6. Recommended Dashboard Visualizations

### Dashboard 1: Clinical Operations Overview
- **KPI Cards**: Total Registered Patients, Total Appointments, Active Prescriptions, Completed Appointments.
- **Donut Chart**: Appointments by Specialty (Cardiology, Primary Care, Urgent Care).
- **Bar Chart**: Top Prescribed Medications by Frequency.
- **Bar Chart**: Vitals Submissions by Metric Type (Blood Pressure, Heart Rate, SpO2, Temperature, Weight).
- **Status Matrix**: Patient Consent Adoption & Revocation Rates.

### Dashboard 2: Multi-Agent Performance & Telemetry
- **KPI Cards**: Total Traces, Average Workflow Latency (ms), Deterministic Safety Escalations, Error Rate.
- **Stacked Bar Chart**: Invocations by Intent (Triage, Scheduling, Records, Reminders, Emergency).
- **Latency Histogram**: Workflow Latency Distribution.
- **Safety Gauge**: 100% Emergency Escalation Precedence & Red-Flag Audit count.

### Dashboard 3: LLM Cost Intelligence & Model Routing
- **KPI Cards**: Total Incurred Cost (USD), Total Prompt Tokens, Total Completion Tokens, Average Cost per Interaction.
- **Bar Chart**: Cost Breakdown by Model (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`).
- **Cost Efficiency Comparison**: Router Tier Distribution (Fast Tier vs. Strong Tier vs. Mock Tier).

---

## 7. Troubleshooting & Verification

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| `HTTP 401 Unauthorized` | Missing or expired JWT bearer token. | Generate a fresh admin token via `POST /auth/login` and update the `AuthToken` parameter in Power BI. |
| `HTTP 403 Forbidden` | Authenticated token belongs to a `patient` user instead of an `admin`. | Log in with an administrator account (e.g. `admin_demo`). |
| `HTTP 404 Not Found` | Incorrect dataset name in `/analytics/export/{dataset_name}`. | Verify the dataset name against the supported list (e.g., `appointments`, `medications`, `vitals`, `consents`, `agent-telemetry`, `cost-intelligence`). |
| `DataFormat.Error` | Content type mismatch in Power Query. | Ensure `format=json` uses `Json.Document` and `format=csv` uses `Csv.Document`. |
