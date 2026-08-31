"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { apiClient, ApiClientError } from "../../../lib/api-client";
import { AppointmentResponse } from "../../../types/api";

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchAppointments = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await apiClient.getMyAppointments();
      setAppointments(data || []);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to load appointments.");
      } else {
        setErrorMessage("Error connecting to appointment service.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAppointments();
  }, [fetchAppointments]);

  const handleCancelAppointment = async (appointmentId: number) => {
    if (!confirm("Are you sure you want to cancel this scheduled consultation?")) {
      return;
    }

    setCancellingId(appointmentId);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.cancelMyAppointment(appointmentId);
      setSuccessMessage(`Appointment #${appointmentId} has been cancelled successfully.`);
      await fetchAppointments();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to cancel appointment.");
      } else {
        setErrorMessage("Error cancelling appointment.");
      }
    } finally {
      setCancellingId(null);
    }
  };

  const scheduled = appointments.filter((a) => a.status === "scheduled");
  const history = appointments.filter((a) => a.status !== "scheduled");

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-3)" }}>
          <div className="flex items-center gap-3">
            <span style={{ fontSize: "2rem" }}>📅</span>
            <div>
              <h2>My Appointments</h2>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                View and manage your scheduled doctor consultations
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={fetchAppointments}
              disabled={isLoading}
              style={{ fontSize: "var(--font-size-xs)" }}
            >
              🔄 Refresh
            </button>

            <Link href="/chat" className="btn btn-primary" style={{ fontSize: "var(--font-size-xs)" }}>
              ➕ Schedule via AI Coordinator
            </Link>
          </div>
        </div>
      </div>

      {/* Success / Error Alerts */}
      {successMessage && (
        <div className="card" style={{ backgroundColor: "var(--status-success-bg)", borderColor: "var(--status-success-border)", padding: "var(--space-3)" }}>
          <p style={{ color: "var(--status-success)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
            ✅ {successMessage}
          </p>
        </div>
      )}

      {errorMessage && (
        <div className="card" style={{ backgroundColor: "var(--status-emergency-bg)", borderColor: "var(--status-emergency-border)", padding: "var(--space-3)" }}>
          <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
            ⚠️ {errorMessage}
          </p>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center" style={{ padding: "var(--space-12) 0" }}>
          <div className="spinner spinner-large" />
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)", marginTop: "var(--space-3)" }}>
            Loading your consultation records...
          </p>
        </div>
      ) : appointments.length === 0 ? (
        /* Empty State */
        <div className="card" style={{ textAlign: "center", padding: "var(--space-12) var(--space-6)" }}>
          <span style={{ fontSize: "3rem", display: "block", marginBottom: "var(--space-3)" }}>🗓️</span>
          <h3 style={{ marginBottom: "var(--space-2)" }}>No Consultations Scheduled</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", maxWidth: "480px", margin: "0 auto var(--space-6) auto" }}>
            You have no upcoming or historical appointments. Engage with the AI Care Coordinator to find specialists and schedule consultations.
          </p>
          <Link href="/chat" className="btn btn-primary">
            💬 Open AI Coordinator
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Scheduled / Upcoming Section */}
          <div>
            <h3 style={{ marginBottom: "var(--space-3)", color: "var(--brand-primary)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span>🟢 Upcoming Consultations</span>
              <span className="badge badge-success" style={{ fontSize: "0.7rem" }}>
                {scheduled.length}
              </span>
            </h3>

            {scheduled.length === 0 ? (
              <div className="card" style={{ padding: "var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
                No active appointments scheduled. Use the AI Care Coordinator to book a consultation.
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "var(--space-4)" }}>
                {scheduled.map((apt) => (
                  <div key={apt.id} className="card" style={{ borderColor: "var(--status-success-border)", borderLeft: "4px solid var(--status-success)" }}>
                    <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-3)" }}>
                      <span className="badge badge-success">Scheduled</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>ID #{apt.id}</span>
                    </div>

                    <div style={{ marginBottom: "var(--space-3)" }}>
                      <h4 style={{ color: "var(--text-primary)", marginBottom: "2px" }}>
                        👨‍⚕️ {apt.doctor_name}
                      </h4>
                      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--brand-primary)", fontWeight: 600 }}>
                        🩺 {apt.specialty}
                      </p>
                    </div>

                    <div style={{ background: "rgba(0, 0, 0, 0.2)", padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)", marginBottom: "var(--space-3)", fontSize: "var(--font-size-xs)" }}>
                      <span style={{ color: "var(--text-muted)" }}>🕒 Date & Time: </span>
                      <strong style={{ color: "var(--text-primary)" }}>{apt.appointment_time}</strong>
                    </div>

                    {apt.notes && (
                      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", fontStyle: "italic", marginBottom: "var(--space-3)" }}>
                        Notes: {apt.notes}
                      </p>
                    )}

                    <div className="flex items-center justify-between" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-3)" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--status-urgent)" }}>
                        ⚠️ Synthetic consultation
                      </span>
                      <button
                        type="button"
                        className="btn btn-danger"
                        onClick={() => handleCancelAppointment(apt.id)}
                        disabled={cancellingId === apt.id}
                        style={{ fontSize: "var(--font-size-xs)", padding: "0.35rem 0.75rem" }}
                      >
                        {cancellingId === apt.id ? "Cancelling..." : "Cancel Appointment"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Historical / Cancelled Section */}
          {history.length > 0 && (
            <div>
              <h3 style={{ marginBottom: "var(--space-3)", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>📁 Past & Cancelled Records</span>
                <span className="badge badge-neutral" style={{ fontSize: "0.7rem" }}>
                  {history.length}
                </span>
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "var(--space-3)" }}>
                {history.map((apt) => (
                  <div key={apt.id} className="card" style={{ opacity: 0.75 }}>
                    <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                      <span className="badge badge-neutral">{apt.status.toUpperCase()}</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>ID #{apt.id}</span>
                    </div>

                    <div style={{ fontSize: "var(--font-size-sm)", fontWeight: 600 }}>
                      👨‍⚕️ {apt.doctor_name} <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>({apt.specialty})</span>
                    </div>
                    <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", marginTop: "4px" }}>
                      🕒 {apt.appointment_time}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
