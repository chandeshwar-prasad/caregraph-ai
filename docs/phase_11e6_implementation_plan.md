# Phase 11E-6 Implementation Plan
## Admin Control Dashboard, Power BI Analytics & Benchmark Scorecards

### 1. Executive Summary
Phase 11E-6 delivers an enterprise-grade administrative intelligence and evaluation suite within the CareGraph AI Next.js application. Building on top of the existing Phase 9 telemetry/benchmarking engine and Phase 11A zero-PHI Power BI aggregation layer, this phase provides executive clinical operations KPIs, multi-agent observability, cost intelligence with model routing savings, direct Power Query export feeds, and 55-scenario quantitative benchmark scorecards.

---

### 2. Architecture & Existing Endpoints

#### Existing FastAPI Backend Endpoints:
- `GET /analytics/clinical-operations` (`ClinicalOperationsAnalyticsResponse`) — Aggregated appointment, medication, vitals, consent, and reminder statistics with server-side zero-PHI enforcement.
- `GET /analytics/agent-telemetry` (`AgentTelemetryAnalyticsResponse`) — Real-time agent latency, safety escalations, error rates, tool breakdowns, and intent distributions.
- `GET /analytics/cost-intelligence` (`CostIntelligenceAnalyticsResponse`) — Token consumption, financial accounting, tier allocations, and model pricing tables.
- `GET /analytics/export/{dataset_name}?format=json|csv` — Direct tabular dataset feeds formatted for Power BI / Power Query.
- `GET /metrics/telemetry` (`TelemetrySummary`) — Real-time operational telemetry summary.
- `GET /metrics/evaluation` (`QuantitativeScorecard`) — Live 55-scenario benchmark quality and safety scorecard.
- `GET /metrics/costs` (`CostSummaryResponse`) — Routing policy metrics and comparative financial savings analysis.

#### Existing Frontend Typed API Client:
All 7 backend endpoints are fully typed in `frontend/src/types/api.ts` and wrapped in `frontend/src/lib/api-client.ts`:
- `apiClient.getClinicalOperationsAnalytics()`
- `apiClient.getAgentTelemetryAnalytics()`
- `apiClient.getCostIntelligenceAnalytics()`
- `apiClient.getExportDatasetUrl(datasetName, format)`
- `apiClient.getTelemetryMetrics()`
- `apiClient.getEvaluationMetrics()`
- `apiClient.getCostMetrics()`

---

### 3. Identified Gaps & Objectives
1. **Admin Navigation & Shell**: Currently `/admin/analytics` and `/admin/benchmarks` render basic `PlaceholderView` components.
2. **Dashboard Overview**: The `/dashboard` view for `admin` role displays navigation cards but lacks live summary KPI metrics.
3. **Power BI Data Feeds**: Need an intuitive UI for exporting CSV/JSON datasets and copying Power Query Web connector endpoints with zero-PHI guarantees.
4. **Benchmark Scorecards**: Need visual gauges, target thresholds, passing indicators, and live evaluation triggers for the 55-scenario test suite.
5. **Role-Based Authorization & Privacy Invariants**: Guarantee non-admin users cannot access administrative data, and verify zero PHI is leaked across metrics or exports.

---

### 4. Recommended Phase 11E-6 Substep Structure

#### Phase 11E-6-1: Admin Dashboard & Executive KPI Overview
- **Scope**: Enhance `/dashboard` for `admin` role with high-level operational KPI cards (Total Patients, System Health, Emergency Safety Recall %, Cumulative Token Spend USD, Average Agent Latency ms).
- **Files**: `frontend/src/app/(authenticated)/dashboard/page.tsx`.

#### Phase 11E-6-2: Clinical Operations & Agent Telemetry Analytics
- **Scope**: Build Tabs 1 & 2 in `/admin/analytics`:
  - Tab 1: Clinical Operations (Appointments by status/specialty/doctor, active vs. inactive medications, vitals by type, consent distribution).
  - Tab 2: Agent Telemetry (Latency breakdown, error rates, safety escalation events, agent distribution, tool usage).
- **Files**: `frontend/src/app/(authenticated)/admin/analytics/page.tsx`, `frontend/src/styles/globals.css`.

#### Phase 11E-6-3: Cost Intelligence & Power BI Export Suite
- **Scope**: Build Tabs 3 & 4 in `/admin/analytics`:
  - Tab 3: Cost Intelligence (Cumulative token accounting, model usage breakdown, tier distribution, routing cost savings %).
  - Tab 4: Power BI Integration (Tabular CSV/JSON export download feeds, Web connector URLs, Power Query M-code snippets).
- **Files**: `frontend/src/app/(authenticated)/admin/analytics/page.tsx`.

#### Phase 11E-6-4: Quantitative Benchmark Scorecards & Evaluation Presentation
- **Scope**: Transform `/admin/benchmarks/page.tsx` into an interactive 55-scenario benchmark scorecard:
  - Safety & Security: Emergency Safety Recall (100.0%), Prompt Injection Resistance (100.0%), Unsupported Claim Rate (0.0%).
  - Agent Accuracy: Intent Classification Accuracy (≥95%), Routing Precision (≥95%), Tool Selection Rate (≥90%).
  - RAG Grounding: Faithfulness (≥95%), Source Attribution Completeness (≥95%).
  - Composite Overall Quality Score index and refresh action.
- **Files**: `frontend/src/app/(authenticated)/admin/benchmarks/page.tsx`.

#### Phase 11E-6-5: Integrated Analytics Verification & Test Suite
- **Scope**: Create comprehensive automated test suite in `frontend/tests/analytics.test.mjs`, run full build, type-check, backend regression, and docker validation.
- **Files**: `frontend/tests/analytics.test.mjs`.

---

### 5. Expected Files to Create / Modify
- `frontend/src/app/(authenticated)/dashboard/page.tsx` (Modify)
- `frontend/src/app/(authenticated)/admin/analytics/page.tsx` (Modify)
- `frontend/src/app/(authenticated)/admin/benchmarks/page.tsx` (Modify)
- `frontend/src/styles/globals.css` (Modify - metric cards, progress rings, export chips)
- `frontend/tests/analytics.test.mjs` (Create)

---

### 6. Security, RBAC & Privacy Invariants
- **Strict Admin RBAC**: All `/admin/*` routes enforce `role === "admin"`. Patients navigating directly receive clear unauthorized notices and redirect prompts.
- **Zero-PHI Compliance**: All analytics data is aggregated server-side. No patient names, phone numbers, notes, or MRNs are present in API responses or exports.
- **No Console Logging**: Zero raw database records or tokens logged in client consoles.
- **Pure Token Identity**: No arbitrary patient/user IDs injected into analytics requests.

---

### 7. Definition of DONE for Phase 11E-6
1. `/dashboard` renders live admin operational KPIs when authenticated as admin.
2. `/admin/analytics` provides 4 responsive tabs (Clinical Operations, Agent Telemetry, Cost Intelligence, Power BI Exports).
3. Power BI dataset exports download cleanly as CSV or JSON with zero PHI.
4. `/admin/benchmarks` renders all 9 quantitative metrics with targets and composite quality score.
5. All automated frontend tests pass (`npm test` ≥95 tests).
6. TypeScript compilation passes with 0 errors (`npm run type-check`).
7. Next.js production build completes cleanly (`npm run build`).
8. Backend regression passes 215/215 tests (`pytest`).
9. Docker Compose validation passes (`docker compose config`).
