"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiClient, ApiClientError } from "../../../lib/api-client";
import { VitalResponse, VitalType } from "../../../types/api";

const VITAL_CONFIGS: Record<string, { label: string; defaultUnit: string; icon: string }> = {
  blood_pressure: { label: "Blood Pressure", defaultUnit: "mmHg", icon: "🩺" },
  heart_rate: { label: "Heart Rate", defaultUnit: "bpm", icon: "❤️" },
  weight: { label: "Weight", defaultUnit: "lbs", icon: "⚖️" },
  temperature: { label: "Temperature", defaultUnit: "°F", icon: "🌡️" },
  spo2: { label: "Oxygen Saturation (SpO2)", defaultUnit: "%", icon: "🫁" },
};

export default function VitalsPage() {
  const [vitals, setVitals] = useState<VitalResponse[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>("all");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form State
  const [vitalType, setVitalType] = useState<VitalType>("blood_pressure");
  const [vitalValue, setVitalValue] = useState<string>("");
  const [vitalUnit, setVitalUnit] = useState<string>("mmHg");
  const [vitalNotes, setVitalNotes] = useState<string>("");

  const fetchVitals = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const typeParam = selectedFilter === "all" ? undefined : selectedFilter;
      const data = await apiClient.getMyVitals(typeParam, 50);
      setVitals(data || []);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to load vital signs.");
      } else {
        setErrorMessage("Error retrieving vital measurements.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [selectedFilter]);

  useEffect(() => {
    fetchVitals();
  }, [fetchVitals]);

  const handleVitalTypeChange = (type: string) => {
    setVitalType(type);
    if (VITAL_CONFIGS[type]) {
      setVitalUnit(VITAL_CONFIGS[type].defaultUnit);
    }
  };

  const handleLogVital = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vitalValue.trim()) {
      setErrorMessage("Please provide a valid measurement value.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.recordMyVital({
        vital_type: vitalType,
        value: vitalValue.trim(),
        unit: vitalUnit.trim() || undefined,
        notes: vitalNotes.trim() || undefined,
      });

      setSuccessMessage("Vital reading recorded successfully.");
      setVitalValue("");
      setVitalNotes("");
      setShowAddForm(false);
      await fetchVitals();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to save vital reading.");
      } else {
        setErrorMessage("Error saving vital measurement.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-3)" }}>
          <div className="flex items-center gap-3">
            <span style={{ fontSize: "2rem" }}>❤️</span>
            <div>
              <h2>Vitals Tracker</h2>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                Log and monitor physiological sign trends for care coordination
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={fetchVitals}
              disabled={isLoading}
              style={{ fontSize: "var(--font-size-xs)" }}
            >
              🔄 Refresh
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setShowAddForm((prev) => !prev)}
              style={{ fontSize: "var(--font-size-xs)" }}
            >
              {showAddForm ? "✕ Close Form" : "➕ Log Reading"}
            </button>
          </div>
        </div>

        {/* Informational Non-Diagnostic Disclaimer */}
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
          ℹ️ <strong>Informational Reference Only:</strong> Measurements are recorded for coordination reference. CareGraph AI does not perform medical diagnosis or interpret clinical normality.
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

      {/* Log Vital Form Drawer */}
      {showAddForm && (
        <div className="card" style={{ borderColor: "var(--brand-primary)" }}>
          <h3 style={{ marginBottom: "var(--space-4)", color: "var(--brand-primary)" }}>
            ➕ Record New Physiological Measurement
          </h3>
          <form onSubmit={handleLogVital}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
              <div>
                <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                  Measurement Type
                </label>
                <select
                  className="select"
                  value={vitalType}
                  onChange={(e) => handleVitalTypeChange(e.target.value)}
                  disabled={isSubmitting}
                >
                  <option value="blood_pressure">🩺 Blood Pressure (e.g. 120/80)</option>
                  <option value="heart_rate">❤️ Heart Rate (e.g. 72)</option>
                  <option value="weight">⚖️ Body Weight (e.g. 165)</option>
                  <option value="temperature">🌡️ Body Temperature (e.g. 98.6)</option>
                  <option value="spo2">🫁 Oxygen Saturation (e.g. 98)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                  Measurement Value
                </label>
                <input
                  type="text"
                  className="input"
                  value={vitalValue}
                  onChange={(e) => setVitalValue(e.target.value)}
                  placeholder={vitalType === "blood_pressure" ? "120/80" : "72"}
                  required
                  disabled={isSubmitting}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                  Unit
                </label>
                <input
                  type="text"
                  className="input"
                  value={vitalUnit}
                  onChange={(e) => setVitalUnit(e.target.value)}
                  placeholder="mmHg, bpm, lbs, °F, %"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div style={{ marginBottom: "var(--space-4)" }}>
              <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                Optional Observation Notes
              </label>
              <input
                type="text"
                className="input"
                value={vitalNotes}
                onChange={(e) => setVitalNotes(e.target.value)}
                placeholder="e.g. Measured at rest, morning reading"
                disabled={isSubmitting}
              />
            </div>

            <div className="flex justify-between items-center">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowAddForm(false)}
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
                {isSubmitting ? "Recording..." : "Save Measurement"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="tab-group" style={{ marginBottom: 0 }}>
        <button
          type="button"
          className={`tab-btn ${selectedFilter === "all" ? "active" : ""}`}
          onClick={() => setSelectedFilter("all")}
        >
          All Types ({vitals.length})
        </button>
        {Object.entries(VITAL_CONFIGS).map(([key, cfg]) => (
          <button
            key={key}
            type="button"
            className={`tab-btn ${selectedFilter === key ? "active" : ""}`}
            onClick={() => setSelectedFilter(key)}
          >
            {cfg.icon} {cfg.label}
          </button>
        ))}
      </div>

      {/* Vitals History Table */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center" style={{ padding: "var(--space-12) 0" }}>
          <div className="spinner spinner-large" />
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)", marginTop: "var(--space-3)" }}>
            Loading recorded measurements...
          </p>
        </div>
      ) : vitals.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "var(--space-12) var(--space-6)" }}>
          <span style={{ fontSize: "3rem", display: "block", marginBottom: "var(--space-3)" }}>📊</span>
          <h3 style={{ marginBottom: "var(--space-2)" }}>No Vital Sign Readings Logged</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", maxWidth: "480px", margin: "0 auto var(--space-4) auto" }}>
            {selectedFilter === "all"
              ? "Start tracking your physiological parameters by logging a new reading."
              : `No readings logged for ${VITAL_CONFIGS[selectedFilter]?.label || selectedFilter}.`}
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowAddForm(true)}
          >
            ➕ Log First Reading
          </button>
        </div>
      ) : (
        <div className="card" style={{ overflowX: "auto", padding: 0 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--font-size-sm)" }}>
            <thead>
              <tr style={{ background: "rgba(0, 0, 0, 0.3)", borderBottom: "1px solid var(--border-default)", textAlign: "left" }}>
                <th style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Type</th>
                <th style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Value</th>
                <th style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Unit</th>
                <th style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Recorded Time</th>
                <th style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>Notes</th>
              </tr>
            </thead>
            <tbody>
              {vitals.map((v) => {
                const cfg = VITAL_CONFIGS[v.vital_type] || { label: v.vital_type, icon: "📊", defaultUnit: "" };
                return (
                  <tr key={v.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <td style={{ padding: "var(--space-3) var(--space-4)", fontWeight: 600 }}>
                      <span style={{ marginRight: "var(--space-2)" }}>{cfg.icon}</span>
                      {cfg.label}
                    </td>
                    <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--brand-primary)", fontWeight: 700 }}>
                      {v.value}
                    </td>
                    <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
                      {v.unit || "-"}
                    </td>
                    <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-dim)", fontSize: "var(--font-size-xs)" }}>
                      {v.recorded_at ? new Date(v.recorded_at).toLocaleString() : "Just now"}
                    </td>
                    <td style={{ padding: "var(--space-3) var(--space-4)", color: "var(--text-secondary)", fontSize: "var(--font-size-xs)", fontStyle: v.notes ? "normal" : "italic" }}>
                      {v.notes || "No notes"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
