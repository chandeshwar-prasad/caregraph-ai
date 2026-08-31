"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiClient, ApiClientError } from "../../../lib/api-client";
import { MedicationReminderResponse } from "../../../types/api";

export default function RemindersPage() {
  const [reminders, setReminders] = useState<MedicationReminderResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [showCreateForm, setShowCreateForm] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form State
  const [reminderText, setReminderText] = useState<string>("");
  const [reminderTime, setReminderTime] = useState<string>("08:00 AM");
  const [reminderNotes, setReminderNotes] = useState<string>("");

  const fetchReminders = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await apiClient.getMyReminders();
      setReminders(data || []);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to load reminders.");
      } else {
        setErrorMessage("Error retrieving medication reminders.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReminders();
  }, [fetchReminders]);

  const handleCreateReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reminderText.trim() || !reminderTime.trim()) {
      setErrorMessage("Please specify both reminder text and time.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.createMyReminder({
        reminder_text: reminderText.trim(),
        reminder_time: reminderTime.trim(),
        notes: reminderNotes.trim() || undefined,
      });

      setSuccessMessage("Medication reminder scheduled successfully.");
      setReminderText("");
      setReminderNotes("");
      setShowCreateForm(false);
      await fetchReminders();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to schedule reminder.");
      } else {
        setErrorMessage("Error creating reminder.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelReminder = async (reminderId: number) => {
    if (!confirm("Are you sure you want to cancel this medication reminder?")) {
      return;
    }

    setCancellingId(reminderId);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.cancelMyReminder(reminderId);
      setSuccessMessage(`Reminder #${reminderId} cancelled.`);
      await fetchReminders();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to cancel reminder.");
      } else {
        setErrorMessage("Error cancelling reminder.");
      }
    } finally {
      setCancellingId(null);
    }
  };

  const activeReminders = reminders.filter((r) => r.status === "active");
  const cancelledReminders = reminders.filter((r) => r.status !== "active");

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-3)" }}>
          <div className="flex items-center gap-3">
            <span style={{ fontSize: "2rem" }}>⏰</span>
            <div>
              <h2>Medication Reminders</h2>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                Automated scheduling alerts and adherence reminders
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={fetchReminders}
              disabled={isLoading}
              style={{ fontSize: "var(--font-size-xs)" }}
            >
              🔄 Refresh
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setShowCreateForm((prev) => !prev)}
              style={{ fontSize: "var(--font-size-xs)" }}
            >
              {showCreateForm ? "✕ Close Form" : "➕ Schedule Reminder"}
            </button>
          </div>
        </div>

        <div
          style={{
            marginTop: "var(--space-4)",
            padding: "var(--space-3)",
            background: "rgba(88, 166, 255, 0.05)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            color: "var(--text-muted)",
          }}
        >
          ℹ️ <strong>Reminders & Privacy Notice:</strong> Reminders require active patient consent. Notifications are scheduling aids and do not replace professional pharmacy directives.
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

      {/* Create Reminder Form Drawer */}
      {showCreateForm && (
        <div className="card" style={{ borderColor: "var(--brand-primary)" }}>
          <h3 style={{ marginBottom: "var(--space-4)", color: "var(--brand-primary)" }}>
            ➕ Schedule New Medication Reminder
          </h3>
          <form onSubmit={handleCreateReminder}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
              <div>
                <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                  Reminder Description
                </label>
                <input
                  type="text"
                  className="input"
                  value={reminderText}
                  onChange={(e) => setReminderText(e.target.value)}
                  placeholder="e.g. Take Lisinopril 10mg with water"
                  required
                  disabled={isSubmitting}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                  Scheduled Time
                </label>
                <input
                  type="text"
                  className="input"
                  value={reminderTime}
                  onChange={(e) => setReminderTime(e.target.value)}
                  placeholder="e.g. 08:00 AM or 20:00"
                  required
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div style={{ marginBottom: "var(--space-4)" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                Optional Instructions / Notes
              </label>
              <input
                type="text"
                className="input"
                value={reminderNotes}
                onChange={(e) => setReminderNotes(e.target.value)}
                placeholder="e.g. Take after breakfast"
                disabled={isSubmitting}
              />
            </div>

            <div className="flex justify-between items-center">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCreateForm(false)}
                disabled={isSubmitting}
                style={{ fontSize: "var(--font-size-xs)" }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSubmitting}
                style={{ fontSize: "var(--font-size-xs)" }}
              >
                {isSubmitting ? "Scheduling..." : "Save Reminder"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center" style={{ padding: "var(--space-12) 0" }}>
          <div className="spinner spinner-large" />
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)", marginTop: "var(--space-3)" }}>
            Loading reminder schedule...
          </p>
        </div>
      ) : reminders.length === 0 ? (
        /* Empty State */
        <div className="card" style={{ textAlign: "center", padding: "var(--space-12) var(--space-6)" }}>
          <span style={{ fontSize: "3rem", display: "block", marginBottom: "var(--space-3)" }}>⏰</span>
          <h3 style={{ marginBottom: "var(--space-2)" }}>No Reminders Scheduled</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", maxWidth: "480px", margin: "0 auto var(--space-4) auto" }}>
            Keep track of your medication schedule by setting up automated coordination reminders.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowCreateForm(true)}
          >
            ➕ Schedule First Reminder
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Active Reminders */}
          <div>
            <h3 style={{ marginBottom: "var(--space-3)", color: "var(--brand-primary)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span>🟢 Active Reminders</span>
              <span className="badge badge-success" style={{ fontSize: "0.7rem" }}>
                {activeReminders.length}
              </span>
            </h3>

            {activeReminders.length === 0 ? (
              <div className="card" style={{ padding: "var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
                No active reminders currently running.
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "var(--space-4)" }}>
                {activeReminders.map((rem) => (
                  <div key={rem.id} className="card" style={{ borderColor: "var(--status-success-border)", borderLeft: "4px solid var(--status-success)" }}>
                    <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                      <span className="badge badge-success">Active</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>ID #{rem.id}</span>
                    </div>

                    <h4 style={{ color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>
                      {rem.reminder_text}
                    </h4>

                    <div style={{ background: "rgba(0, 0, 0, 0.2)", padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)", marginBottom: "var(--space-3)", fontSize: "var(--font-size-xs)" }}>
                      <span style={{ color: "var(--text-muted)" }}>⏰ Scheduled Time: </span>
                      <strong style={{ color: "var(--brand-primary)" }}>{rem.reminder_time}</strong>
                    </div>

                    {rem.notes && (
                      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", fontStyle: "italic", marginBottom: "var(--space-3)" }}>
                        Notes: {rem.notes}
                      </p>
                    )}

                    <div className="flex justify-end" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-3)" }}>
                      <button
                        type="button"
                        className="btn btn-danger"
                        onClick={() => handleCancelReminder(rem.id)}
                        disabled={cancellingId === rem.id}
                        style={{ fontSize: "var(--font-size-xs)", padding: "0.3rem 0.7rem" }}
                      >
                        {cancellingId === rem.id ? "Cancelling..." : "Cancel Reminder"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Cancelled Reminders */}
          {cancelledReminders.length > 0 && (
            <div>
              <h3 style={{ marginBottom: "var(--space-3)", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span>📁 Past & Cancelled Reminders</span>
                <span className="badge badge-neutral" style={{ fontSize: "0.7rem" }}>
                  {cancelledReminders.length}
                </span>
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "var(--space-3)" }}>
                {cancelledReminders.map((rem) => (
                  <div key={rem.id} className="card" style={{ opacity: 0.7 }}>
                    <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-1)" }}>
                      <span className="badge badge-neutral">Cancelled</span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>ID #{rem.id}</span>
                    </div>
                    <div style={{ fontSize: "var(--font-size-sm)", color: "var(--text-muted)" }}>
                      <s>{rem.reminder_text}</s> at {rem.reminder_time}
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
