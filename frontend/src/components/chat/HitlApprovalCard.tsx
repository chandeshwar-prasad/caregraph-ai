"use client";

import React from "react";
import Link from "next/link";
import { SlotDetails, ApprovalStatus } from "../../types/api";

interface HitlApprovalCardProps {
  slot: SlotDetails;
  approvalStatus?: ApprovalStatus | null;
  onApprove?: () => Promise<void>;
  onReject?: () => Promise<void>;
  isSubmitting?: boolean;
}

export const HitlApprovalCard: React.FC<HitlApprovalCardProps> = ({
  slot,
  approvalStatus = "pending",
  onApprove,
  onReject,
  isSubmitting = false,
}) => {
  const doctor = slot.doctor_name || "Assigned Specialist";
  const specialty = slot.specialty || "General Medicine";
  const time = slot.appointment_time || "Requested Time Slot";
  const isMock = slot.is_mock ?? true;

  return (
    <div className="hitl-approval-card" role="region" aria-label="Appointment Confirmation">
      <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
        <div className="flex items-center gap-2">
          <span style={{ fontSize: "1.2rem" }}>📋</span>
          <h4 style={{ color: "var(--brand-primary)", margin: 0 }}>
            Human-in-the-Loop Appointment Verification
          </h4>
        </div>
        {approvalStatus === "approved" && (
          <span className="badge badge-success">Confirmed</span>
        )}
        {approvalStatus === "rejected" && (
          <span className="badge badge-emergency">Declined</span>
        )}
        {approvalStatus === "pending" && (
          <span className="badge badge-urgent">Action Required</span>
        )}
      </div>

      <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-2)" }}>
        This appointment has not been booked yet. Review the details below, then choose Approve &amp; Book or Decline.
      </p>

      <table className="hitl-table">
        <tbody>
          <tr>
            <td className="label">👨‍⚕️ Provider</td>
            <td className="value">{doctor}</td>
          </tr>
          <tr>
            <td className="label">🩺 Specialty</td>
            <td className="value">{specialty}</td>
          </tr>
          <tr>
            <td className="label">🕒 Schedule</td>
            <td className="value">{time}</td>
          </tr>
        </tbody>
      </table>

      {isMock && (
        <p style={{ fontSize: "0.72rem", color: "var(--status-urgent)", marginBottom: "var(--space-4)" }}>
          ⚠️ <em>Synthetic evaluation mode — mock consultation booking without external EHR impact.</em>
        </p>
      )}

      {/* Action Buttons if Pending */}
      {approvalStatus === "pending" && onApprove && onReject && (
        <div className="flex gap-3" style={{ flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onApprove}
            disabled={isSubmitting}
            style={{ flex: 1, minWidth: "160px" }}
          >
            {isSubmitting ? (
              <div className="flex items-center gap-2">
                <div className="spinner" />
                <span>Confirming...</span>
              </div>
            ) : (
              "✅ Approve & Book Appointment"
            )}
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={onReject}
            disabled={isSubmitting}
            style={{ flex: 1, minWidth: "140px" }}
          >
            ❌ Decline Request
          </button>
        </div>
      )}

      {/* Resolved States */}
      {approvalStatus === "approved" && (
        <div className="flex items-center justify-between" style={{ marginTop: "var(--space-3)", flexWrap: "wrap", gap: "var(--space-2)" }}>
          <span style={{ color: "var(--status-success)", fontSize: "var(--font-size-xs)", fontWeight: 600 }}>
            ✅ Appointment verified and recorded in synthetic database.
          </span>
          <Link href="/appointments" className="btn btn-secondary" style={{ fontSize: "var(--font-size-xs)", padding: "0.3rem 0.7rem" }}>
            View in Appointments →
          </Link>
        </div>
      )}

      {approvalStatus === "rejected" && (
        <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600, marginTop: "var(--space-3)" }}>
          ❌ Booking request was declined. No consultation was scheduled.
        </p>
      )}
    </div>
  );
};
