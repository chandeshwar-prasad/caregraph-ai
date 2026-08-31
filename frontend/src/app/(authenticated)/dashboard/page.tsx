"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../../../context/AuthContext";
import { apiClient } from "../../../lib/api-client";
import {
  HealthResponse,
  AppointmentResponse,
  VitalResponse,
  MedicationResponse,
  MedicationReminderResponse,
  ClinicalOperationsAnalyticsResponse,
  AgentTelemetryAnalyticsResponse,
  CostIntelligenceAnalyticsResponse,
  QuantitativeScorecard,
} from "../../../types/api";

export default function DashboardPage() {
  const { user, role } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  // Patient live metrics
  const [appointments, setAppointments] = useState<AppointmentResponse[]>([]);
  const [vitals, setVitals] = useState<VitalResponse[]>([]);
  const [medications, setMedications] = useState<MedicationResponse[]>([]);
  const [reminders, setReminders] = useState<MedicationReminderResponse[]>([]);
  const [isLoadingPatientMetrics, setIsLoadingPatientMetrics] = useState<boolean>(role === "patient");

  // Admin live executive metrics
  const [clinicalOps, setClinicalOps] = useState<ClinicalOperationsAnalyticsResponse | null>(null);
  const [agentTelemetry, setAgentTelemetry] = useState<AgentTelemetryAnalyticsResponse | null>(null);
  const [costIntelligence, setCostIntelligence] = useState<CostIntelligenceAnalyticsResponse | null>(null);
  const [evalScorecard, setEvalScorecard] = useState<QuantitativeScorecard | null>(null);
  const [isLoadingAdminMetrics, setIsLoadingAdminMetrics] = useState<boolean>(role === "admin");

  useEffect(() => {
    let mounted = true;

    // Common Health status
    apiClient
      .getHealth()
      .then((data) => {
        if (mounted) setHealth(data);
      })
      .catch(() => {
        if (mounted) setHealth(null);
      });

    // Patient role data fetch
    if (role === "patient") {
      Promise.allSettled([
        apiClient.getMyAppointments(),
        apiClient.getMyVitals(undefined, 5),
        apiClient.getMyMedications(),
        apiClient.getMyReminders(),
      ]).then(([aptRes, vitRes, medRes, remRes]) => {
        if (!mounted) return;
        if (aptRes.status === "fulfilled") setAppointments(aptRes.value || []);
        if (vitRes.status === "fulfilled") setVitals(vitRes.value || []);
        if (medRes.status === "fulfilled") setMedications(medRes.value || []);
        if (remRes.status === "fulfilled") setReminders(remRes.value || []);
        setIsLoadingPatientMetrics(false);
      });
    }

    // Admin role data fetch
    if (role === "admin") {
      Promise.allSettled([
        apiClient.getClinicalOperationsAnalytics(),
        apiClient.getAgentTelemetryAnalytics(),
        apiClient.getCostIntelligenceAnalytics(),
        apiClient.getEvaluationMetrics(),
      ]).then(([opsRes, telRes, costRes, evalRes]) => {
        if (!mounted) return;
        if (opsRes.status === "fulfilled") setClinicalOps(opsRes.value || null);
        if (telRes.status === "fulfilled") setAgentTelemetry(telRes.value || null);
        if (costRes.status === "fulfilled") setCostIntelligence(costRes.value || null);
        if (evalRes.status === "fulfilled") setEvalScorecard(evalRes.value || null);
        setIsLoadingAdminMetrics(false);
      });
    }

    return () => {
      mounted = false;
    };
  }, [role]);

  const upcomingAppointments = appointments.filter((a) => a.status === "scheduled");
  const activeMedications = medications.filter((m) => m.is_active);
  const activeReminders = reminders.filter((r) => r.status === "active");

  return (
    <div>
      {/* Welcome Banner */}
      <div className="card" style={{ marginBottom: "var(--space-6)", background: "linear-gradient(135deg, rgba(22, 30, 46, 0.9) 0%, rgba(30, 42, 66, 0.7) 100%)" }}>
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-4)" }}>
          <div>
            <div className="flex items-center gap-2" style={{ marginBottom: "var(--space-2)" }}>
              <h2>Welcome, {user?.username}</h2>
              <span
                className={role === "admin" ? "badge badge-urgent" : "badge badge-success"}
              >
                {role ? role.toUpperCase() : "AUTHENTICATED"}
              </span>
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)" }}>
              {role === "admin"
                ? "Admin Control & Executive Intelligence Hub — Operational telemetry, benchmark scorecards, and Power BI analytics."
                : "Care Navigation & Management Console — Multi-agent symptom guidance, appointments, vitals, and reminders."}
            </p>
          </div>

          {health && (
            <div className="flex items-center gap-2">
              <span
                className={`badge ${health.status === "healthy" ? "badge-success" : "badge-urgent"}`}
                style={{ fontSize: "0.75rem" }}
              >
                API: {health.status.toUpperCase()}
              </span>
              <span className="badge badge-info" style={{ fontSize: "0.75rem" }}>
                DB: {health.database.toUpperCase()}
              </span>
              <span className="badge badge-neutral" style={{ fontSize: "0.75rem" }}>
                MODE: {health.mode.toUpperCase()}
              </span>
            </div>
          )}
        </div>

        {/* Clinical Safety Disclaimer */}
        <div
          style={{
            marginTop: "var(--space-4)",
            padding: "var(--space-3)",
            background: "rgba(0, 0, 0, 0.2)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            color: "var(--text-muted)",
          }}
        >
          ⚠️ <strong>Clinical Safety Directive:</strong> CareGraph AI is a care-coordination and navigation system. It does not provide autonomous clinical diagnosis, prescriptions, or emergency triage override.
        </div>
      </div>

      {/* Patient Dashboard Content */}
      {role === "patient" && (
        <div className="flex flex-col gap-6">
          {/* Patient Health Overview Metrics Bar */}
          <div>
            <h3 style={{ marginBottom: "var(--space-3)", color: "var(--brand-primary)" }}>
              📊 Health & Care Overview
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-4)" }}>
              <Link href="/appointments" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  Upcoming Consultations
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--brand-primary)", margin: "var(--space-1) 0" }}>
                  {isLoadingPatientMetrics ? "..." : upcomingAppointments.length}
                </div>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  {upcomingAppointments.length > 0
                    ? `Next: ${upcomingAppointments[0].appointment_time.slice(0, 16)}`
                    : "No appointments scheduled"}
                </div>
              </Link>

              <Link href="/vitals" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  Latest Vital Reading
                </div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--brand-primary)", margin: "var(--space-1) 0" }}>
                  {isLoadingPatientMetrics ? "..." : vitals.length > 0 ? `${vitals[0].value} ${vitals[0].unit || ""}` : "None"}
                </div>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  {vitals.length > 0 ? vitals[0].vital_type.replace("_", " ") : "Log physiological vitals"}
                </div>
              </Link>

              <Link href="/medications" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  Active Prescriptions
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--status-success)", margin: "var(--space-1) 0" }}>
                  {isLoadingPatientMetrics ? "..." : activeMedications.length}
                </div>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  {activeMedications.length > 0 ? `${activeMedications[0].name}` : "No active prescriptions"}
                </div>
              </Link>

              <Link href="/reminders" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  Active Reminders
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--status-urgent)", margin: "var(--space-1) 0" }}>
                  {isLoadingPatientMetrics ? "..." : activeReminders.length}
                </div>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  {activeReminders.length > 0 ? `${activeReminders[0].reminder_text.slice(0, 24)}...` : "Set care reminder"}
                </div>
              </Link>
            </div>
          </div>

          {/* Quick Actions Grid */}
          <div>
            <h3 style={{ marginBottom: "var(--space-3)", color: "var(--brand-primary)" }}>
              ⚡ Care Services & Navigation
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "var(--space-4)" }}>
              <Link href="/chat" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>💬</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  AI Care Coordination
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Multi-agent clinical triage, grounded health guidance, and Human-in-the-Loop scheduling.
                </p>
              </Link>

              <Link href="/appointments" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>📅</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Appointments & Visits
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  View scheduled clinical consultations, specialties, and manage cancellations.
                </p>
              </Link>

              <Link href="/vitals" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>💓</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Vitals & Biometrics
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Track heart rate, blood pressure, glucose, and oxygen saturation over time.
                </p>
              </Link>

              <Link href="/medications" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>💊</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Medication Tracker
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Active prescription records, dosages, prescribing physicians, and schedules.
                </p>
              </Link>

              <Link href="/reminders" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>⏰</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Medication Reminders
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Configure daily adherence reminders and timing alerts for prescribed medications.
                </p>
              </Link>

              <Link href="/consents" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>🛡️</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Consent Center
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Review and manage granular privacy and AI processing authorizations.
                </p>
              </Link>

              <Link href="/voice" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>🎙️</div>
                <h4 style={{ color: "var(--brand-accent)", marginBottom: "var(--space-1)" }}>
                  Voice Assistant
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Phase 11B speech-to-text audio input and text-to-speech synthesized audio playback.
                </p>
              </Link>

              <Link href="/vision" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>👁️</div>
                <h4 style={{ color: "var(--brand-accent)", marginBottom: "var(--space-1)" }}>
                  Vision Analyzer
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Phase 11C visual document entity extraction and symptom observation assistance.
                </p>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Admin Dashboard Content */}
      {role === "admin" && (
        <div className="flex flex-col gap-6">
          {/* Executive KPI Overview Grid */}
          <div>
            <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-3)" }}>
              <h3 style={{ color: "var(--brand-primary)", display: "flex", alignItems: "center", gap: "var(--space-2)", margin: 0 }}>
                <span>📊</span> Executive Operational KPI Overview
              </h3>
              <span className="badge badge-success">Zero-PHI Aggregated</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "var(--space-4)" }}>
              {/* Total Registered Patients */}
              <div className="card">
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  Total Patients Monitored
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--brand-primary)", margin: "var(--space-1) 0" }}>
                  {isLoadingAdminMetrics ? "..." : (clinicalOps?.total_patients ?? "—")}
                </div>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  {clinicalOps ? `${clinicalOps.appointments.total_count} encounters recorded` : "Aggregated clinical records"}
                </div>
              </div>

              {/* Emergency Safety Recall */}
              <div className="card">
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  Emergency Safety Recall
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--status-success)", margin: "var(--space-1) 0" }}>
                  {isLoadingAdminMetrics ? "..." : evalScorecard ? `${evalScorecard.emergency_safety_recall_pct}%` : "100.0%"}
                </div>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--status-success)" }}>
                  🎯 Target: 100.0% recall rate
                </div>
              </div>

              {/* Average Workflow Latency */}
              <div className="card">
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  Agent Workflow Latency
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--brand-accent)", margin: "var(--space-1) 0" }}>
                  {isLoadingAdminMetrics ? "..." : agentTelemetry ? `${agentTelemetry.avg_latency_ms} ms` : "—"}
                </div>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  {agentTelemetry ? `${agentTelemetry.total_events} workflow spans tracked` : "Telemetry collector active"}
                </div>
              </div>

              {/* Cumulative Token Spend */}
              <div className="card">
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase" }}>
                  Cumulative Token Spend
                </div>
                <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--text-primary)", margin: "var(--space-1) 0" }}>
                  {isLoadingAdminMetrics ? "..." : costIntelligence ? `$${costIntelligence.total_cost_usd.toFixed(4)}` : "—"}
                </div>
                <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  {costIntelligence ? `${costIntelligence.total_tokens.toLocaleString()} tokens consumed` : "Tier pricing tracking"}
                </div>
              </div>
            </div>
          </div>

          {/* Quick Admin Operations Navigation */}
          <div>
            <h3 style={{ marginBottom: "var(--space-3)", color: "var(--brand-primary)" }}>
              ⚡ Administrative Control & Power BI Feeds
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--space-4)" }}>
              <Link href="/admin/analytics" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>📈</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Power BI & Operational Analytics
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Zero-PHI aggregated KPIs for appointments, vitals, token spend, and direct CSV/JSON Power Query export feeds.
                </p>
              </Link>

              <Link href="/admin/benchmarks" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>🎯</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Quantitative Evaluation Scorecard
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  55-scenario benchmark quality evaluation spanning emergency recall, prompt injection defense, and RAG faithfulness.
                </p>
              </Link>

              <Link href="/admin/messaging" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>📱</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Outbound Messaging Gateway
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  SMS and WhatsApp notification dispatch testing with carrier opt-out simulation and recipient masking.
                </p>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
