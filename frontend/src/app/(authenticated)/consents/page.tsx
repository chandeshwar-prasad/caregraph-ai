"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiClient, ApiClientError } from "../../../lib/api-client";
import { ConsentResponse, ConsentType } from "../../../types/api";

interface ConsentDefinition {
  type: ConsentType;
  title: string;
  description: string;
  icon: string;
}

const CONSENT_CATALOG: ConsentDefinition[] = [
  {
    type: "ai_processing",
    title: "AI Workflow & Triage Routing",
    description: "Authorize LangGraph supervisor to route queries to specialized triage and care workflows.",
    icon: "🧬",
  },
  {
    type: "appointment_booking",
    title: "Appointment Coordination & Booking",
    description: "Authorize scheduling workflow to search availability and hold mock consultation slots.",
    icon: "📅",
  },
  {
    type: "vital_tracking",
    title: "Vitals Logging & Storage",
    description: "Authorize recording and retrieval of blood pressure, heart rate, and physiological vitals.",
    icon: "❤️",
  },
  {
    type: "medication_tracking",
    title: "Medication Records Retrieval",
    description: "Authorize the assistant to inspect active prescription records for care coordination.",
    icon: "💊",
  },
  {
    type: "medication_reminders",
    title: "Medication Reminder Notifications",
    description: "Authorize automated scheduling and delivery of medication adherence alerts.",
    icon: "⏰",
  },
  {
    type: "data_access",
    title: "General Patient Record Access",
    description: "Authorize access to demographics and synthetic patient profile records.",
    icon: "📋",
  },
];

export default function ConsentsPage() {
  const [consents, setConsents] = useState<ConsentResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [updatingType, setUpdatingType] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchConsents = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await apiClient.getMyConsents();
      setConsents(data || []);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to load consents.");
      } else {
        setErrorMessage("Error retrieving privacy consent records.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConsents();
  }, [fetchConsents]);

  const handleGrantConsent = async (consentType: ConsentType) => {
    setUpdatingType(consentType);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.grantMyConsent({
        consent_type: consentType,
        expires_days: 365,
        version: "v1.0",
      });
      setSuccessMessage(`Consent for '${consentType}' granted successfully.`);
      await fetchConsents();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to grant consent.");
      } else {
        setErrorMessage("Error granting consent.");
      }
    } finally {
      setUpdatingType(null);
    }
  };

  const handleRevokeConsent = async (consentType: ConsentType) => {
    if (!confirm(`Are you sure you want to revoke consent for '${consentType}'? Associated features may be disabled by backend security policies.`)) {
      return;
    }

    setUpdatingType(consentType);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await apiClient.revokeMyConsent({
        consent_type: consentType,
      });
      setSuccessMessage(`Consent for '${consentType}' has been revoked.`);
      await fetchConsents();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Failed to revoke consent.");
      } else {
        setErrorMessage("Error revoking consent.");
      }
    } finally {
      setUpdatingType(null);
    }
  };

  const getConsentRecord = (type: string) => {
    return consents.find((c) => c.consent_type === type);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-3)" }}>
          <div className="flex items-center gap-3">
            <span style={{ fontSize: "2rem" }}>🛡️</span>
            <div>
              <h2>Patient Consent Center</h2>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                Granular authorization controls for AI processing and medical data categories
              </p>
            </div>
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchConsents}
            disabled={isLoading}
            style={{ fontSize: "var(--font-size-xs)" }}
          >
            🔄 Refresh Status
          </button>
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
          🔒 <strong>Zero-Trust Authorization Invariant:</strong> The CareGraph AI backend deterministically verifies active consent before executing agent tools. Revoking consent immediately blocks server-side access to that category.
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
            Loading active consent policies...
          </p>
        </div>
      ) : (
        /* Consent Catalog Grid */
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "var(--space-4)" }}>
          {CONSENT_CATALOG.map((item) => {
            const record = getConsentRecord(item.type);
            const isGranted = record?.status === "granted";
            const isUpdating = updatingType === item.type;

            return (
              <div
                key={item.type}
                className="card"
                style={{
                  borderLeft: `4px solid ${isGranted ? "var(--status-success)" : "var(--status-emergency)"}`,
                }}
              >
                <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                  <span style={{ fontSize: "1.5rem" }}>{item.icon}</span>
                  <span className={isGranted ? "badge badge-success" : "badge badge-emergency"}>
                    {isGranted ? "Granted" : record ? record.status.toUpperCase() : "Not Granted"}
                  </span>
                </div>

                <h3 style={{ fontSize: "var(--font-size-base)", color: "var(--text-primary)", marginBottom: "var(--space-1)" }}>
                  {item.title}
                </h3>
                <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-4)", minHeight: "36px" }}>
                  {item.description}
                </p>

                {record && (
                  <div style={{ background: "rgba(0, 0, 0, 0.2)", padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius-sm)", marginBottom: "var(--space-4)", fontSize: "0.72rem", color: "var(--text-dim)" }}>
                    <div>Policy: {record.version}</div>
                    <div>Granted: {new Date(record.granted_at).toLocaleDateString()}</div>
                    {record.expires_at && <div>Expires: {new Date(record.expires_at).toLocaleDateString()}</div>}
                  </div>
                )}

                <div className="flex justify-end" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-3)" }}>
                  {isGranted ? (
                    <button
                      type="button"
                      className="btn btn-danger"
                      onClick={() => handleRevokeConsent(item.type)}
                      disabled={isUpdating}
                      style={{ fontSize: "var(--font-size-xs)", padding: "0.35rem 0.75rem" }}
                    >
                      {isUpdating ? "Updating..." : "Revoke Consent"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => handleGrantConsent(item.type)}
                      disabled={isUpdating}
                      style={{ fontSize: "var(--font-size-xs)", padding: "0.35rem 0.75rem" }}
                    >
                      {isUpdating ? "Updating..." : "Grant Consent"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
