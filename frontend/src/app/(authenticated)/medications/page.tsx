"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { apiClient, ApiClientError } from "../../../lib/api-client";
import { MedicationResponse } from "../../../types/api";

export default function MedicationsPage() {
  const [medications, setMedications] = useState<MedicationResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchMedications = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await apiClient.getMyMedications();
      setMedications(data || []);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to load medications.");
      } else {
        setErrorMessage("Error retrieving medication list.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMedications();
  }, [fetchMedications]);

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-3)" }}>
          <div className="flex items-center gap-3">
            <span style={{ fontSize: "2rem" }}>💊</span>
            <div>
              <h2>Active Medications</h2>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                View your active prescribed medications and clinical instructions
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={fetchMedications}
              disabled={isLoading}
              style={{ fontSize: "var(--font-size-xs)" }}
            >
              🔄 Refresh
            </button>
            <Link href="/reminders" className="btn btn-primary" style={{ fontSize: "var(--font-size-xs)" }}>
              ⏰ Manage Reminders
            </Link>
          </div>
        </div>

        {/* Clinical Safety Disclaimer */}
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
          ℹ️ <strong>Clinical Safety Notice:</strong> CareGraph AI displays prescribed medication records for care coordination reference only. The assistant never alters dosages, prescribes drugs, or changes physician orders.
        </div>
      </div>

      {/* Error Alert */}
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
            Loading active prescriptions...
          </p>
        </div>
      ) : medications.length === 0 ? (
        /* Empty State */
        <div className="card" style={{ textAlign: "center", padding: "var(--space-12) var(--space-6)" }}>
          <span style={{ fontSize: "3rem", display: "block", marginBottom: "var(--space-3)" }}>💊</span>
          <h3 style={{ marginBottom: "var(--space-2)" }}>No Active Medications Found</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", maxWidth: "480px", margin: "0 auto var(--space-4) auto" }}>
            No prescribed medications are currently registered in your synthetic patient profile.
          </p>
          <Link href="/chat" className="btn btn-secondary">
            💬 Discuss with Care Coordinator
          </Link>
        </div>
      ) : (
        /* Medication Cards Grid */
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "var(--space-4)" }}>
          {medications.map((med) => (
            <div key={med.id} className="card" style={{ borderLeft: "4px solid var(--brand-primary)" }}>
              <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-3)" }}>
                <span className="badge badge-success">
                  {med.is_active ? "Active Prescription" : "Inactive"}
                </span>
                <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>ID #{med.id}</span>
              </div>

              <h3 style={{ color: "var(--brand-primary)", marginBottom: "var(--space-1)" }}>
                {med.name}
              </h3>
              <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-primary)", fontWeight: 600, marginBottom: "var(--space-3)" }}>
                Dosage: {med.dosage}
              </p>

              <div style={{ background: "rgba(0, 0, 0, 0.2)", padding: "var(--space-3)", borderRadius: "var(--radius-sm)", marginBottom: "var(--space-3)", fontSize: "var(--font-size-xs)" }}>
                <div style={{ marginBottom: "4px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Frequency: </span>
                  <strong style={{ color: "var(--text-primary)" }}>{med.frequency}</strong>
                </div>
                <div style={{ marginBottom: "4px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Prescribed By: </span>
                  <span style={{ color: "var(--text-secondary)" }}>{med.prescribed_by || "Attending Physician"}</span>
                </div>
                {med.start_date && (
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>Start Date: </span>
                    <span style={{ color: "var(--text-secondary)" }}>{med.start_date}</span>
                  </div>
                )}
              </div>

              {med.notes && (
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", fontStyle: "italic", marginBottom: "var(--space-3)" }}>
                  Instructions: {med.notes}
                </p>
              )}

              <div className="flex items-center justify-end" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-3)" }}>
                <Link
                  href="/reminders"
                  className="btn btn-secondary"
                  style={{ fontSize: "var(--font-size-xs)", padding: "0.35rem 0.75rem" }}
                >
                  ⏰ Set Reminder
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
