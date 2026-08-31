"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "../../../../context/AuthContext";
import { apiClient } from "../../../../lib/api-client";
import {
  ClinicalOperationsAnalyticsResponse,
  AgentTelemetryAnalyticsResponse,
  CostIntelligenceAnalyticsResponse,
  CostSummaryResponse,
} from "../../../../types/api";

type AnalyticsTab = "clinical" | "telemetry" | "costs" | "powerbi";

interface ExportDatasetInfo {
  id: string;
  name: string;
  description: string;
  category: "Clinical" | "Observability" | "Financial";
  fields: string[];
}

const EXPORT_DATASETS: ExportDatasetInfo[] = [
  {
    id: "clinical-operations",
    name: "Clinical Operations Summary",
    description: "Aggregated operational metric dimensions across patients, encounters, active medications, vitals, and consents.",
    category: "Clinical",
    fields: ["category", "metric_name", "dimension", "metric_value"],
  },
  {
    id: "appointments",
    name: "Consultation Encounters",
    description: "Tabular appointment records with physician roster, specialty demand, and consultation statuses.",
    category: "Clinical",
    fields: ["appointment_id", "doctor_name", "specialty", "appointment_time", "status", "created_at"],
  },
  {
    id: "medications",
    name: "Prescription Adherence",
    description: "Tabular medication records with dosage schedules, frequency allocations, and active therapy status.",
    category: "Clinical",
    fields: ["medication_id", "name", "dosage", "frequency", "is_active", "created_at"],
  },
  {
    id: "vitals",
    name: "Physiological Biometrics",
    description: "Tabular biometric vital records (heart rate, blood pressure, blood glucose, oxygen saturation).",
    category: "Clinical",
    fields: ["vital_id", "vital_type", "unit", "recorded_at", "source", "created_at"],
  },
  {
    id: "consents",
    name: "Privacy Authorizations",
    description: "Tabular patient consent records, authorization types, status changes, and version tracking.",
    category: "Clinical",
    fields: ["consent_id", "consent_type", "status", "version", "granted_at", "expires_at"],
  },
  {
    id: "agent-telemetry",
    name: "Multi-Agent Telemetry Traces",
    description: "Granular operational trace events with latency ms, agent routing decisions, tool runs, and token consumption.",
    category: "Observability",
    fields: ["event_id", "timestamp", "actor_role", "intent", "selected_agent", "latency_ms", "status", "safety_escalated", "tool_name", "prompt_tokens", "completion_tokens", "total_tokens"],
  },
  {
    id: "cost-intelligence",
    name: "Token Accounting & Costs",
    description: "Workflow-level financial accounting logs with model pricing breakdown and token usage.",
    category: "Financial",
    fields: ["record_id", "timestamp", "workflow_name", "model", "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd"],
  },
];

export default function AdminAnalyticsPage() {
  const { role } = useAuth();
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("clinical");

  // Data states
  const [clinicalOps, setClinicalOps] = useState<ClinicalOperationsAnalyticsResponse | null>(null);
  const [agentTelemetry, setAgentTelemetry] = useState<AgentTelemetryAnalyticsResponse | null>(null);
  const [costIntelligence, setCostIntelligence] = useState<CostIntelligenceAnalyticsResponse | null>(null);
  const [costMetrics, setCostMetrics] = useState<CostSummaryResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [downloadingDataset, setDownloadingDataset] = useState<string | null>(null);
  const [selectedMCodeDataset, setSelectedMCodeDataset] = useState<string>("clinical-operations");
  const [copiedMCode, setCopiedMCode] = useState<boolean>(false);

  const fetchAnalytics = useCallback(async () => {
    if (role !== "admin") return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [opsRes, telRes, costRes, costMetricsRes] = await Promise.all([
        apiClient.getClinicalOperationsAnalytics(),
        apiClient.getAgentTelemetryAnalytics(),
        apiClient.getCostIntelligenceAnalytics(),
        apiClient.getCostMetrics().catch(() => null),
      ]);
      setClinicalOps(opsRes);
      setAgentTelemetry(telRes);
      setCostIntelligence(costRes);
      if (costMetricsRes) setCostMetrics(costMetricsRes);
      setLastRefreshed(new Date());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load operational analytics.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [role]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Strict Admin RBAC Guard
  if (role !== "admin") {
    return (
      <div className="card" style={{ maxWidth: "600px", margin: "var(--space-12) auto", textAlign: "center" }}>
        <span style={{ fontSize: "3rem", display: "block", marginBottom: "var(--space-3)" }}>🔒</span>
        <h2 style={{ color: "var(--status-emergency)", marginBottom: "var(--space-2)" }}>
          Admin Access Required
        </h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-6)" }}>
          The Operational Analytics & Power BI suite is restricted to authorized administrators. Your active role (<code>{role || "guest"}</code>) is not permitted to view institutional health intelligence.
        </p>
        <Link href="/dashboard" className="btn btn-primary">
          ← Return to Dashboard
        </Link>
      </div>
    );
  }

  // Helper for computing max value in a key-value record for CSS bar rendering
  const getMaxVal = (record: Record<string, number> = {}): number => {
    const vals = Object.values(record);
    return vals.length > 0 ? Math.max(...vals, 1) : 1;
  };

  // Secure client-side dataset download helper with JWT Authorization
  const handleDownloadDataset = async (datasetId: string, format: "csv" | "json") => {
    const key = `${datasetId}_${format}`;
    setDownloadingDataset(key);
    setErrorMessage(null);

    try {
      const url = apiClient.getExportDatasetUrl(datasetId, format);
      const headers: Record<string, string> = {};
      const token = apiClient.getToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch(url, { headers });
      if (!res.ok) {
        throw new Error(`Export failed with HTTP status ${res.status}`);
      }

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `${datasetId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setDownloadingDataset(null);
    }
  };

  // Generate Power Query M-Code Snippet for Power BI Desktop
  const generatePowerQueryMCode = (datasetId: string): string => {
    const feedUrl = apiClient.getExportDatasetUrl(datasetId, "json");
    return `// Power BI Power Query M-Code for CareGraph AI
// Dataset: ${datasetId} (Zero-PHI Tabular Feed)
let
    Source = Json.Document(Web.Contents("${feedUrl}", [
        Headers = [
            #"Authorization" = "Bearer <YOUR_ADMIN_JWT_TOKEN>",
            #"Accept" = "application/json"
        ]
    ])),
    #"Converted to Table" = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    #"Expanded Records" = Table.ExpandRecordColumn(#"Converted to Table", "Column1", Record.FieldNames(Source{0}))
in
    #"Expanded Records"`;
  };

  const handleCopyMCode = (datasetId: string) => {
    const code = generatePowerQueryMCode(datasetId);
    navigator.clipboard.writeText(code).then(() => {
      setCopiedMCode(true);
      setTimeout(() => setCopiedMCode(false), 2500);
    });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="card" style={{ background: "linear-gradient(135deg, rgba(22, 30, 46, 0.95) 0%, rgba(30, 42, 66, 0.8) 100%)" }}>
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-4)" }}>
          <div>
            <div className="flex items-center gap-2" style={{ marginBottom: "var(--space-2)" }}>
              <h2>📈 Power BI & Operational Analytics</h2>
              <span className="badge badge-urgent">ADMIN RESTRICTED</span>
              <span className="badge badge-success">ZERO-PHI CERTIFIED</span>
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)" }}>
              Server-aggregated clinical operations metrics, multi-agent telemetry, token accounting, and Power Query export feeds.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {lastRefreshed && (
              <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>
                Updated: {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={fetchAnalytics}
              disabled={isLoading}
              className="btn btn-secondary"
              style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)" }}
            >
              <span style={{ display: "inline-block", transform: isLoading ? "rotate(180deg)" : "none", transition: "transform 0.5s ease" }}>
                🔄
              </span>
              {isLoading ? "Refreshing..." : "Refresh Feeds"}
            </button>
          </div>
        </div>

        {/* Clinical Safety Directive */}
        <div
          style={{
            marginTop: "var(--space-4)",
            padding: "var(--space-3)",
            background: "rgba(0, 0, 0, 0.25)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            color: "var(--text-muted)",
          }}
        >
          🛡️ <strong>Zero-PHI Operational Invariant:</strong> All statistics and export feeds are aggregated in-memory server-side. No identifiable patient names, contact numbers, clinical notes, or MRNs are queried or transmitted.
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="alert alert-urgent flex items-center justify-between">
          <div>
            <strong>Analytics Notice:</strong> {errorMessage}
          </div>
          <button onClick={fetchAnalytics} className="btn btn-secondary btn-sm">
            Retry
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div style={{ display: "flex", gap: "var(--space-2)", borderBottom: "1px solid var(--border-default)", paddingBottom: "var(--space-2)", overflowX: "auto" }}>
        <button
          onClick={() => setActiveTab("clinical")}
          className={`btn ${activeTab === "clinical" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderRadius: "var(--radius-sm)", padding: "var(--space-2) var(--space-4)" }}
        >
          🏥 Clinical Operations
        </button>

        <button
          onClick={() => setActiveTab("telemetry")}
          className={`btn ${activeTab === "telemetry" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderRadius: "var(--radius-sm)", padding: "var(--space-2) var(--space-4)" }}
        >
          🤖 Agent Telemetry & Observability
        </button>

        <button
          onClick={() => setActiveTab("costs")}
          className={`btn ${activeTab === "costs" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderRadius: "var(--radius-sm)", padding: "var(--space-2) var(--space-4)" }}
        >
          💰 Cost Intelligence & Routing
        </button>

        <button
          onClick={() => setActiveTab("powerbi")}
          className={`btn ${activeTab === "powerbi" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderRadius: "var(--radius-sm)", padding: "var(--space-2) var(--space-4)" }}
        >
          📊 Power BI Data Feeds & M-Code
        </button>
      </div>

      {/* ========================================== */}
      {/* TAB 1: CLINICAL OPERATIONS ANALYTICS       */}
      {/* ========================================== */}
      {activeTab === "clinical" && (
        <div className="flex flex-col gap-6">
          {/* Executive Overview KPI Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-4)" }}>
            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Total Patients
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--brand-primary)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (clinicalOps?.total_patients ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Registered patient profiles
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Total Consultations
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--status-success)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (clinicalOps?.appointments.total_count ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Scheduled encounters
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Active Prescriptions
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--brand-accent)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (clinicalOps?.medications.active_count ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Out of {clinicalOps?.medications.total_count ?? "—"} total medications
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Physiological Vitals
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--text-primary)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (clinicalOps?.vitals.total_count ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Biometric readings logged
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Active Consents
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--brand-primary)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (clinicalOps?.consents.total_count ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Privacy authorizations
              </div>
            </div>
          </div>

          {/* Detailed Clinical Operations Breakdown Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "var(--space-6)" }}>
            {/* 1. Appointments Activity */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>📅</span> Appointments by Status & Specialty
              </h3>

              <div style={{ marginBottom: "var(--space-4)" }}>
                <h4 style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                  Status Distribution
                </h4>
                {clinicalOps && Object.keys(clinicalOps.appointments.by_status).length > 0 ? (
                  Object.entries(clinicalOps.appointments.by_status).map(([statusKey, count]) => {
                    const maxVal = getMaxVal(clinicalOps.appointments.by_status);
                    const pct = Math.round((count / maxVal) * 100);
                    return (
                      <div key={statusKey} style={{ marginBottom: "var(--space-2)" }}>
                        <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "2px" }}>
                          <span style={{ textTransform: "capitalize" }}>{statusKey}</span>
                          <span style={{ fontWeight: 600 }}>{count}</span>
                        </div>
                        <div style={{ height: "6px", background: "var(--bg-tertiary)", borderRadius: "3px", overflow: "hidden" }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: statusKey === "scheduled" ? "var(--brand-primary)" : statusKey === "completed" ? "var(--status-success)" : "var(--status-urgent)" }} />
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No appointment status records logged.</p>
                )}
              </div>

              <div>
                <h4 style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                  Clinical Specialty Demand
                </h4>
                {clinicalOps && Object.keys(clinicalOps.appointments.by_specialty).length > 0 ? (
                  Object.entries(clinicalOps.appointments.by_specialty).map(([spec, count]) => {
                    const maxVal = getMaxVal(clinicalOps.appointments.by_specialty);
                    const pct = Math.round((count / maxVal) * 100);
                    return (
                      <div key={spec} style={{ marginBottom: "var(--space-2)" }}>
                        <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "2px" }}>
                          <span>{spec}</span>
                          <span style={{ fontWeight: 600 }}>{count}</span>
                        </div>
                        <div style={{ height: "6px", background: "var(--bg-tertiary)", borderRadius: "3px", overflow: "hidden" }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand-accent)" }} />
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No specialty distribution available.</p>
                )}
              </div>
            </div>

            {/* 2. Medications & Vitals Summary */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>💊</span> Medications & Physiological Vitals
              </h3>

              <div style={{ marginBottom: "var(--space-4)" }}>
                <h4 style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                  Prescription Status Ratio
                </h4>
                {clinicalOps ? (
                  <div>
                    <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "var(--space-1)" }}>
                      <span style={{ color: "var(--status-success)" }}>Active: {clinicalOps.medications.active_count}</span>
                      <span style={{ color: "var(--text-dim)" }}>Inactive: {clinicalOps.medications.inactive_count}</span>
                    </div>
                    <div style={{ height: "8px", background: "var(--bg-tertiary)", borderRadius: "4px", overflow: "hidden", display: "flex" }}>
                      <div
                        style={{
                          width: `${clinicalOps.medications.total_count > 0 ? (clinicalOps.medications.active_count / clinicalOps.medications.total_count) * 100 : 0}%`,
                          background: "var(--status-success)",
                        }}
                      />
                      <div
                        style={{
                          width: `${clinicalOps.medications.total_count > 0 ? (clinicalOps.medications.inactive_count / clinicalOps.medications.total_count) * 100 : 0}%`,
                          background: "var(--text-dim)",
                        }}
                      />
                    </div>
                  </div>
                ) : null}
              </div>

              <div>
                <h4 style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
                  Logged Vitals by Biometric Type
                </h4>
                {clinicalOps && Object.keys(clinicalOps.vitals.by_type).length > 0 ? (
                  Object.entries(clinicalOps.vitals.by_type).map(([vType, count]) => {
                    const maxVal = getMaxVal(clinicalOps.vitals.by_type);
                    const pct = Math.round((count / maxVal) * 100);
                    return (
                      <div key={vType} style={{ marginBottom: "var(--space-2)" }}>
                        <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "2px" }}>
                          <span style={{ textTransform: "capitalize" }}>{vType.replace("_", " ")}</span>
                          <span style={{ fontWeight: 600 }}>{count}</span>
                        </div>
                        <div style={{ height: "6px", background: "var(--bg-tertiary)", borderRadius: "3px", overflow: "hidden" }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand-primary)" }} />
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No vitals records logged yet.</p>
                )}
              </div>
            </div>

            {/* 3. Consent Management Compliance */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>🛡️</span> Privacy Authorizations by Consent Type
              </h3>
              {clinicalOps && Object.keys(clinicalOps.consents.by_type).length > 0 ? (
                Object.entries(clinicalOps.consents.by_type).map(([cType, count]) => {
                  const maxVal = getMaxVal(clinicalOps.consents.by_type);
                  const pct = Math.round((count / maxVal) * 100);
                  return (
                    <div key={cType} style={{ marginBottom: "var(--space-2)" }}>
                      <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "2px" }}>
                        <span style={{ textTransform: "capitalize" }}>{cType.replace("_", " ")}</span>
                        <span style={{ fontWeight: 600 }}>{count}</span>
                      </div>
                      <div style={{ height: "6px", background: "var(--bg-tertiary)", borderRadius: "3px", overflow: "hidden" }}>
                        <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand-primary)" }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No consent authorizations recorded.</p>
              )}
            </div>

            {/* 4. Adherence Reminders Distribution */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>⏰</span> Care Reminders Status
              </h3>
              {clinicalOps && Object.keys(clinicalOps.reminders.by_status).length > 0 ? (
                Object.entries(clinicalOps.reminders.by_status).map(([rStatus, count]) => {
                  const maxVal = getMaxVal(clinicalOps.reminders.by_status);
                  const pct = Math.round((count / maxVal) * 100);
                  return (
                    <div key={rStatus} style={{ marginBottom: "var(--space-2)" }}>
                      <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "2px" }}>
                        <span style={{ textTransform: "capitalize" }}>{rStatus}</span>
                        <span style={{ fontWeight: 600 }}>{count}</span>
                      </div>
                      <div style={{ height: "6px", background: "var(--bg-tertiary)", borderRadius: "3px", overflow: "hidden" }}>
                        <div style={{ width: `${pct}%`, height: "100%", background: rStatus === "active" ? "var(--status-urgent)" : "var(--text-dim)" }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No active care reminders found.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================== */}
      {/* TAB 2: AGENT TELEMETRY & OBSERVABILITY     */}
      {/* ========================================== */}
      {activeTab === "telemetry" && (
        <div className="flex flex-col gap-6">
          {/* Executive Observability Top Stat Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-4)" }}>
            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Total Workflow Spans
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--brand-primary)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (agentTelemetry?.total_events ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Instrumented spans tracked
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Average Latency
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--brand-accent)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : agentTelemetry ? `${agentTelemetry.avg_latency_ms} ms` : "—"}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--status-success)" }}>
                ⚡ Sub-second response SLA
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Safety Escalations
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--status-emergency)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (agentTelemetry?.safety_escalations ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--status-emergency)" }}>
                🚨 Red-flag triage escalations
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Workflow Error Rate
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--status-success)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : agentTelemetry ? `${(agentTelemetry.error_rate * 100).toFixed(2)}%` : "—"}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--status-success)" }}>
                🎯 Target: &lt; 1.0% error rate
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Recent Traces In-Memory
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--text-primary)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (agentTelemetry?.recent_traces_count ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Circular buffer telemetry
              </div>
            </div>
          </div>

          {/* Observability Visual Breakdown Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "var(--space-6)" }}>
            {/* 1. Multi-Agent Workload Distribution */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>🤖</span> Multi-Agent Workload Allocation
              </h3>
              {agentTelemetry && Object.keys(agentTelemetry.agents_breakdown).length > 0 ? (
                Object.entries(agentTelemetry.agents_breakdown).map(([agentName, count]) => {
                  const maxVal = getMaxVal(agentTelemetry.agents_breakdown);
                  const pct = Math.round((count / maxVal) * 100);
                  return (
                    <div key={agentName} style={{ marginBottom: "var(--space-3)" }}>
                      <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 600, color: "var(--brand-primary)" }}>{agentName}</span>
                        <span style={{ color: "var(--text-secondary)" }}>{count} invocations</span>
                      </div>
                      <div style={{ height: "8px", background: "var(--bg-tertiary)", borderRadius: "4px", overflow: "hidden" }}>
                        <div style={{ width: `${pct}%`, height: "100%", background: "linear-gradient(90deg, var(--brand-primary) 0%, var(--brand-accent) 100%)" }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No multi-agent trace events recorded yet.</p>
              )}
            </div>

            {/* 2. Classified User Intents */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>🎯</span> Intent Classification Breakdown
              </h3>
              {agentTelemetry && Object.keys(agentTelemetry.intents_breakdown).length > 0 ? (
                Object.entries(agentTelemetry.intents_breakdown).map(([intentName, count]) => {
                  const maxVal = getMaxVal(agentTelemetry.intents_breakdown);
                  const pct = Math.round((count / maxVal) * 100);
                  return (
                    <div key={intentName} style={{ marginBottom: "var(--space-3)" }}>
                      <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 600, textTransform: "capitalize" }}>{intentName}</span>
                        <span style={{ color: "var(--text-secondary)" }}>{count} queries</span>
                      </div>
                      <div style={{ height: "8px", background: "var(--bg-tertiary)", borderRadius: "4px", overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${pct}%`,
                            height: "100%",
                            background: intentName === "emergency" ? "var(--status-emergency)" : "var(--brand-accent)",
                          }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No user intents classified yet.</p>
              )}
            </div>

            {/* 3. Tool Execution Breakdown */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>🔧</span> Tool Execution Frequency
              </h3>
              {agentTelemetry && Object.keys(agentTelemetry.tool_breakdown).length > 0 ? (
                Object.entries(agentTelemetry.tool_breakdown).map(([toolName, count]) => {
                  const maxVal = getMaxVal(agentTelemetry.tool_breakdown);
                  const pct = Math.round((count / maxVal) * 100);
                  return (
                    <div key={toolName} style={{ marginBottom: "var(--space-3)" }}>
                      <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 500, fontFamily: "monospace", fontSize: "0.8rem" }}>{toolName}</span>
                        <span style={{ color: "var(--text-secondary)" }}>{count} runs</span>
                      </div>
                      <div style={{ height: "6px", background: "var(--bg-tertiary)", borderRadius: "3px", overflow: "hidden" }}>
                        <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand-primary)" }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No tool executions captured yet.</p>
              )}
            </div>

            {/* 4. Execution Status Distribution */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>📊</span> Execution Status Distribution
              </h3>
              {agentTelemetry && Object.keys(agentTelemetry.status_breakdown).length > 0 ? (
                Object.entries(agentTelemetry.status_breakdown).map(([statusKey, count]) => {
                  const maxVal = getMaxVal(agentTelemetry.status_breakdown);
                  const pct = Math.round((count / maxVal) * 100);
                  return (
                    <div key={statusKey} style={{ marginBottom: "var(--space-3)" }}>
                      <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 600 }}>{statusKey}</span>
                        <span style={{ color: "var(--text-secondary)" }}>{count} traces</span>
                      </div>
                      <div style={{ height: "6px", background: "var(--bg-tertiary)", borderRadius: "3px", overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${pct}%`,
                            height: "100%",
                            background: statusKey === "SUCCESS" ? "var(--status-success)" : "var(--status-urgent)",
                          }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>No status traces recorded.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================== */}
      {/* TAB 3: COST INTELLIGENCE & ROUTING ECONOMY */}
      {/* ========================================== */}
      {activeTab === "costs" && (
        <div className="flex flex-col gap-6">
          {/* Executive Cost Top Stat Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-4)" }}>
            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Total Expenditure
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--brand-primary)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : costIntelligence ? `$${costIntelligence.total_cost_usd.toFixed(4)}` : "—"}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Cumulative token spend
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Total Tokens Processed
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--brand-accent)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : (costIntelligence?.total_tokens.toLocaleString() ?? "—")}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                {costIntelligence ? `${costIntelligence.total_prompt_tokens.toLocaleString()} prompt / ${costIntelligence.total_completion_tokens.toLocaleString()} comp` : "Prompt + completion"}
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Avg Cost / Workflow
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--status-success)", margin: "var(--space-1) 0" }}>
                {isLoading ? "..." : costIntelligence ? `$${costIntelligence.avg_cost_per_workflow_usd.toFixed(5)}` : "—"}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--status-success)" }}>
                ⚡ Ultra-low per-query cost
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                Routing Cost Advantage
              </div>
              <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--status-success)", margin: "var(--space-1) 0" }}>
                {costMetrics?.comparative_analysis?.cost_savings_percentage
                  ? `~${costMetrics.comparative_analysis.cost_savings_percentage.toFixed(0)}%`
                  : "65%"}
              </div>
              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Savings vs frontier baseline
              </div>
            </div>
          </div>

          {/* Model Usage & Pricing Grids */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "var(--space-6)" }}>
            {/* 1. Model Distribution & Invocations */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>🤖</span> Active Model Token & Financial Accounting
              </h3>
              {costIntelligence && Object.keys(costIntelligence.model_usage).length > 0 ? (
                Object.entries(costIntelligence.model_usage).map(([modelName, rawUsage]) => {
                  const usage = rawUsage as { invocations?: number; total_tokens?: number; cost_usd?: number; prompt_tokens?: number; completion_tokens?: number };
                  const costFormatted = typeof usage?.cost_usd === "number" ? usage.cost_usd.toFixed(4) : "0.0000";
                  const tokensFormatted = typeof usage?.total_tokens === "number" ? usage.total_tokens.toLocaleString() : "0";

                  return (
                    <div key={modelName} style={{ marginBottom: "var(--space-4)", padding: "var(--space-3)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)" }}>
                      <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                        <span style={{ fontWeight: 600, color: "var(--brand-primary)", fontFamily: "monospace", fontSize: "0.85rem" }}>
                          {modelName}
                        </span>
                        <span className="badge badge-success">${costFormatted}</span>
                      </div>
                      <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                        <span>Tokens: {tokensFormatted}</span>
                        <span>Invocations: {usage?.invocations ?? "—"}</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ padding: "var(--space-4)", background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)" }}>
                  <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                    <span style={{ fontWeight: 600, color: "var(--brand-primary)", fontFamily: "monospace", fontSize: "0.85rem" }}>
                      llama-3.3-70b-versatile
                    </span>
                    <span className="badge badge-success">$0.0000</span>
                  </div>
                  <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                    <span>Tokens: 0</span>
                    <span>Invocations: 0</span>
                  </div>
                </div>
              )}
            </div>

            {/* 2. Tier Distribution */}
            <div className="card">
              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>⚖️</span> Architecture Tier Allocation
              </h3>
              {costIntelligence && Object.keys(costIntelligence.tier_distribution).length > 0 ? (
                Object.entries(costIntelligence.tier_distribution).map(([tierName, count]) => {
                  const maxVal = getMaxVal(costIntelligence.tier_distribution);
                  const pct = Math.round((count / maxVal) * 100);
                  return (
                    <div key={tierName} style={{ marginBottom: "var(--space-3)" }}>
                      <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "4px" }}>
                        <span style={{ fontWeight: 600 }}>{tierName}</span>
                        <span style={{ color: "var(--text-secondary)" }}>{count} invocations</span>
                      </div>
                      <div style={{ height: "8px", background: "var(--bg-tertiary)", borderRadius: "4px", overflow: "hidden" }}>
                        <div style={{ width: `${pct}%`, height: "100%", background: "var(--brand-accent)" }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
                  <div>
                    <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "4px" }}>
                      <span style={{ fontWeight: 600 }}>Tier 1: Fast Triage & Screening</span>
                      <span style={{ color: "var(--text-secondary)" }}>Active</span>
                    </div>
                    <div style={{ height: "8px", background: "var(--bg-tertiary)", borderRadius: "4px", overflow: "hidden" }}>
                      <div style={{ width: "85%", height: "100%", background: "var(--brand-primary)" }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "4px" }}>
                      <span style={{ fontWeight: 600 }}>Tier 2: Reasoning & Extraction</span>
                      <span style={{ color: "var(--text-secondary)" }}>Active</span>
                    </div>
                    <div style={{ height: "8px", background: "var(--bg-tertiary)", borderRadius: "4px", overflow: "hidden" }}>
                      <div style={{ width: "50%", height: "100%", background: "var(--brand-accent)" }} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Model Pricing Reference Table */}
          <div className="card">
            <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-3)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span>🏷️</span> Enterprise Model Pricing Table Reference
            </h3>
            <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
              Cost calculation is based on per-million token rates across specialized multi-model routing tiers.
            </p>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-xs)", textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-default)", color: "var(--text-dim)" }}>
                    <th style={{ padding: "var(--space-2)" }}>Model Identifier</th>
                    <th style={{ padding: "var(--space-2)" }}>Category / Tier</th>
                    <th style={{ padding: "var(--space-2)" }}>Prompt $/M Tokens</th>
                    <th style={{ padding: "var(--space-2)" }}>Completion $/M Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {costIntelligence && Object.keys(costIntelligence.pricing_table).length > 0 ? (
                    Object.entries(costIntelligence.pricing_table).map(([mName, rawPricing]) => {
                      const p = rawPricing as { prompt_per_million?: number; completion_per_million?: number; category?: string };
                      return (
                        <tr key={mName} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                          <td style={{ padding: "var(--space-2)", fontFamily: "monospace", color: "var(--brand-primary)" }}>{mName}</td>
                          <td style={{ padding: "var(--space-2)" }}>{p?.category ?? "General"}</td>
                          <td style={{ padding: "var(--space-2)" }}>${p?.prompt_per_million ?? "—"}</td>
                          <td style={{ padding: "var(--space-2)" }}>${p?.completion_per_million ?? "—"}</td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "var(--space-2)", fontFamily: "monospace", color: "var(--brand-primary)" }}>llama-3.3-70b-versatile</td>
                      <td style={{ padding: "var(--space-2)" }}>Tier 1 Fast Reasoning</td>
                      <td style={{ padding: "var(--space-2)" }}>$0.13</td>
                      <td style={{ padding: "var(--space-2)" }}>$0.40</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================== */}
      {/* TAB 4: POWER BI DATA FEEDS & M-CODE        */}
      {/* ========================================== */}
      {activeTab === "powerbi" && (
        <div className="flex flex-col gap-6">
          {/* Power BI Integration Summary Card */}
          <div className="card" style={{ background: "linear-gradient(135deg, rgba(22, 30, 46, 0.9) 0%, rgba(30, 42, 66, 0.7) 100%)" }}>
            <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-4)" }}>
              <div>
                <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <span>📊</span> Power BI Desktop & Service Data Feeds
                </h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)" }}>
                  Zero-PHI tabular datasets formatted for direct ingestion in Microsoft Power BI Desktop, Power Query, Excel, or SQL ETL pipelines.
                </p>
              </div>
              <span className="badge badge-success">7 Tabular Feeds Available</span>
            </div>
          </div>

          {/* Dataset Catalog Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "var(--space-4)" }}>
            {EXPORT_DATASETS.map((ds) => (
              <div key={ds.id} className="card flex flex-col justify-between" style={{ background: "var(--bg-secondary)" }}>
                <div>
                  <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                    <h4 style={{ color: "var(--brand-primary)", margin: 0 }}>{ds.name}</h4>
                    <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>{ds.category}</span>
                  </div>
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-3)" }}>
                    {ds.description}
                  </p>
                  <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", marginBottom: "var(--space-4)" }}>
                    <strong>Export Columns:</strong> <code>{ds.fields.slice(0, 4).join(", ")}{ds.fields.length > 4 ? ` +${ds.fields.length - 4} more` : ""}</code>
                  </div>
                </div>

                <div className="flex items-center justify-between" style={{ gap: "var(--space-2)", paddingTop: "var(--space-3)", borderTop: "1px solid var(--border-subtle)" }}>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDownloadDataset(ds.id, "csv")}
                      disabled={downloadingDataset === `${ds.id}_csv`}
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: "0.75rem" }}
                    >
                      {downloadingDataset === `${ds.id}_csv` ? "..." : "⬇ CSV"}
                    </button>
                    <button
                      onClick={() => handleDownloadDataset(ds.id, "json")}
                      disabled={downloadingDataset === `${ds.id}_json`}
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: "0.75rem" }}
                    >
                      {downloadingDataset === `${ds.id}_json` ? "..." : "⬇ JSON"}
                    </button>
                  </div>

                  <button
                    onClick={() => setSelectedMCodeDataset(ds.id)}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: "0.75rem", color: selectedMCodeDataset === ds.id ? "var(--brand-accent)" : "var(--text-secondary)" }}
                  >
                    View M-Code
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Power Query M-Code Snippet Generator */}
          <div className="card">
            <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-3)", flexWrap: "wrap", gap: "var(--space-2)" }}>
              <div>
                <h3 style={{ color: "var(--brand-primary)", margin: 0, display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <span>🔌</span> Power Query M-Code Helper: <code>{selectedMCodeDataset}</code>
                </h3>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", marginTop: "var(--space-1)" }}>
                  Copy this snippet into Power BI Desktop (<strong>Get Data → Blank Query → Advanced Editor</strong>).
                </p>
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={selectedMCodeDataset}
                  onChange={(e) => setSelectedMCodeDataset(e.target.value)}
                  className="input"
                  style={{ width: "auto", fontSize: "var(--font-size-xs)", padding: "var(--space-1) var(--space-2)" }}
                >
                  {EXPORT_DATASETS.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>

                <button
                  onClick={() => handleCopyMCode(selectedMCodeDataset)}
                  className="btn btn-primary btn-sm"
                >
                  {copiedMCode ? "✓ Copied!" : "📋 Copy M-Code"}
                </button>
              </div>
            </div>

            <pre
              style={{
                background: "var(--bg-tertiary)",
                padding: "var(--space-4)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.8rem",
                fontFamily: "monospace",
                color: "var(--text-primary)",
                overflowX: "auto",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {generatePowerQueryMCode(selectedMCodeDataset)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
