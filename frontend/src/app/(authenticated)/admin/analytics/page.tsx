"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "../../../../context/AuthContext";
import { apiClient } from "../../../../lib/api-client";
import {
  ClinicalOperationsAnalyticsResponse,
  AgentTelemetryAnalyticsResponse,
} from "../../../../types/api";

type AnalyticsTab = "clinical" | "telemetry" | "costs" | "powerbi";

export default function AdminAnalyticsPage() {
  const { role } = useAuth();
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("clinical");

  // Data states
  const [clinicalOps, setClinicalOps] = useState<ClinicalOperationsAnalyticsResponse | null>(null);
  const [agentTelemetry, setAgentTelemetry] = useState<AgentTelemetryAnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchAnalytics = useCallback(async () => {
    if (role !== "admin") return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [opsRes, telRes] = await Promise.all([
        apiClient.getClinicalOperationsAnalytics(),
        apiClient.getAgentTelemetryAnalytics(),
      ]);
      setClinicalOps(opsRes);
      setAgentTelemetry(telRes);
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
          🛡️ <strong>Zero-PHI Operational Invariant:</strong> All statistics below are aggregated in-memory server-side. No identifiable patient names, contact numbers, clinical notes, or MRNs are queried or transmitted.
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="alert alert-urgent flex items-center justify-between">
          <div>
            <strong>Analytics Fetch Error:</strong> {errorMessage}
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
          style={{ borderRadius: "var(--radius-sm)", padding: "var(--space-2) var(--space-4)", opacity: 0.8 }}
        >
          💰 Cost Intelligence <span className="badge badge-info" style={{ marginLeft: "var(--space-1)", fontSize: "0.7rem" }}>Phase 11E-6-3</span>
        </button>

        <button
          onClick={() => setActiveTab("powerbi")}
          className={`btn ${activeTab === "powerbi" ? "btn-primary" : "btn-secondary"}`}
          style={{ borderRadius: "var(--radius-sm)", padding: "var(--space-2) var(--space-4)", opacity: 0.8 }}
        >
          📊 Power BI Data Feeds <span className="badge badge-info" style={{ marginLeft: "var(--space-1)", fontSize: "0.7rem" }}>Phase 11E-6-3</span>
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
      {/* TAB 3 & 4 PLACEHOLDERS (Phase 11E-6-3)     */}
      {/* ========================================== */}
      {activeTab === "costs" && (
        <div className="card" style={{ textAlign: "center", padding: "var(--space-12)" }}>
          <div style={{ fontSize: "3rem", marginBottom: "var(--space-2)" }}>💰</div>
          <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-2)" }}>
            Cost Intelligence & Routing Economy
          </h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "550px", margin: "0 auto var(--space-4) auto" }}>
            Cumulative token expenditure, model pricing tier distribution, and model router comparative financial savings will be activated in <strong>Phase 11E-6-3</strong>.
          </p>
          <span className="badge badge-info">Scheduled for Phase 11E-6-3</span>
        </div>
      )}

      {activeTab === "powerbi" && (
        <div className="card" style={{ textAlign: "center", padding: "var(--space-12)" }}>
          <div style={{ fontSize: "3rem", marginBottom: "var(--space-2)" }}>📊</div>
          <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-2)" }}>
            Power BI Desktop Feeds & M-Code Exports
          </h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "550px", margin: "0 auto var(--space-4) auto" }}>
            Direct CSV and JSON download feeds and Power Query Web.Contents integration snippets for executive reporting will be activated in <strong>Phase 11E-6-3</strong>.
          </p>
          <span className="badge badge-info">Scheduled for Phase 11E-6-3</span>
        </div>
      )}
    </div>
  );
}
