"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "../../../context/AuthContext";
import { apiClient } from "../../../lib/api-client";
import { HealthResponse } from "../../../types/api";

export default function DashboardPage() {
  const { user, role, patientProfile } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    apiClient
      .getHealth()
      .then((data) => {
        if (mounted) setHealth(data);
      })
      .catch(() => {
        if (mounted) setHealth(null);
      });

    return () => {
      mounted = false;
    };
  }, []);

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
                ? "Admin Control & Clinical Intelligence Hub — Operational telemetry, benchmark scorecards, and Power BI analytics."
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
            </div>
          )}
        </div>
      </div>

      {/* Patient Dashboard Content */}
      {role === "patient" && (
        <div className="flex flex-col gap-6">
          {/* Patient Demographics Card */}
          <div className="card">
            <h3 style={{ marginBottom: "var(--space-3)", color: "var(--brand-primary)" }}>
              📋 Patient Profile
            </h3>
            {patientProfile ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-4)" }}>
                <div>
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>Full Name</span>
                  <div style={{ fontWeight: 600 }}>{patientProfile.first_name} {patientProfile.last_name}</div>
                </div>
                <div>
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>Gender / DOB</span>
                  <div>{patientProfile.gender || "Not specified"} ({patientProfile.date_of_birth || "N/A"})</div>
                </div>
                <div>
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>Email</span>
                  <div>{patientProfile.email || "N/A"}</div>
                </div>
                <div>
                  <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>Phone</span>
                  <div>{patientProfile.phone || "N/A"}</div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-3)" }}>
                <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
                  Synthetic patient profile is active for <strong>{user?.username}</strong>.
                </p>
                <span className="badge badge-info">Profile Active</span>
              </div>
            )}
          </div>

          {/* Quick Navigation Cards Grid */}
          <div>
            <h3 style={{ marginBottom: "var(--space-4)", color: "var(--text-primary)" }}>
              🚀 Care Coordination Modules
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--space-4)" }}>
              <Link href="/chat" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>💬</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  AI Care Coordinator
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Engage in multi-agent symptom triage, doctor search, and appointment scheduling.
                </p>
              </Link>

              <Link href="/appointments" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>📅</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Appointments
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  View, track, and manage your scheduled doctor consultations.
                </p>
              </Link>

              <Link href="/vitals" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>❤️</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Vitals Tracker
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Log and monitor blood pressure, heart rate, weight, and SpO2 readings.
                </p>
              </Link>

              <Link href="/medications" className="card card-interactive" style={{ textDecoration: "none" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>💊</div>
                <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                  Medications & Reminders
                </h4>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                  Track active prescriptions and schedule automated reminder notifications.
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
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "var(--space-4)" }}>
            <Link href="/admin/analytics" className="card card-interactive" style={{ textDecoration: "none" }}>
              <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>📈</div>
              <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                Power BI & Operational Analytics
              </h4>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                Zero-PHI aggregated KPIs for appointments, vitals, token spend, and CSV/JSON export feeds.
              </p>
            </Link>

            <Link href="/admin/benchmarks" className="card card-interactive" style={{ textDecoration: "none" }}>
              <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>🎯</div>
              <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                Quantitative Evaluation Scorecard
              </h4>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                55-scenario benchmark quality evaluation spanning safety recall, injection defense, and RAG faithfulness.
              </p>
            </Link>

            <Link href="/admin/messaging" className="card card-interactive" style={{ textDecoration: "none" }}>
              <div style={{ fontSize: "1.8rem", marginBottom: "var(--space-2)" }}>📱</div>
              <h4 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                Messaging Gateway
              </h4>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
                SMS and WhatsApp notification dispatch testing with keyword opt-out verification.
              </p>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
