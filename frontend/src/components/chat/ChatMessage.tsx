"use client";

import React, { useState } from "react";
import { GroundingSource, SlotDetails, RiskLevel, ApprovalStatus } from "../../types/api";
import { HitlApprovalCard } from "./HitlApprovalCard";

export interface ChatMessageProps {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  riskLevel?: RiskLevel | null;
  safetyEscalated?: boolean;
  sources?: GroundingSource[];
  followUpQuestions?: string[];
  approvalRequired?: boolean;
  approvalStatus?: ApprovalStatus | null;
  selectedSlot?: SlotDetails | null;
  onApprove?: () => Promise<void>;
  onReject?: () => Promise<void>;
  onSelectFollowUp?: (question: string) => void;
  isApproving?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  role,
  content,
  intent,
  riskLevel,
  safetyEscalated = false,
  sources = [],
  followUpQuestions = [],
  approvalRequired = false,
  approvalStatus,
  selectedSlot,
  onApprove,
  onReject,
  onSelectFollowUp,
  isApproving = false,
}) => {
  const [showSources, setShowSources] = useState(false);
  const isEmergency = safetyEscalated || riskLevel === "emergency";
  const isUrgent = !isEmergency && riskLevel === "urgent";

  return (
    <div className={`message-row ${role}`} role="article" aria-label={`${role} message`}>
      <div className={`message-avatar ${role}`} aria-hidden="true">
        {role === "user" ? "👤" : "🧬"}
      </div>

      <div style={{ flex: 1, maxWidth: "100%" }}>
        {/* Emergency Alert Header (for Assistant messages) */}
        {role === "assistant" && isEmergency && (
          <div className="emergency-alert-card" role="alert">
            <span style={{ fontSize: "1.4rem" }}>🚨</span>
            <div>
              <h4 style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-sm)", margin: 0, fontWeight: 700 }}>
                EMERGENCY CLINICAL ESCALATION
              </h4>
              <p style={{ color: "var(--text-primary)", fontSize: "var(--font-size-xs)", margin: "4px 0 0 0" }}>
                Red-flag clinical symptoms identified. Immediate evaluation required. Call <strong>911 / 112</strong> or proceed to the nearest emergency department.
              </p>
            </div>
          </div>
        )}

        {/* Urgent Alert Header */}
        {role === "assistant" && isUrgent && (
          <div
            className="card"
            style={{
              backgroundColor: "var(--status-urgent-bg)",
              borderColor: "var(--status-urgent-border)",
              padding: "var(--space-3)",
              marginBottom: "var(--space-3)",
            }}
          >
            <div className="flex items-center gap-2">
              <span>⚠️</span>
              <span style={{ color: "var(--status-urgent)", fontSize: "var(--font-size-xs)", fontWeight: 700 }}>
                PROMPT MEDICAL EVALUATION ADVISED: Urgent symptoms detected.
              </span>
            </div>
          </div>
        )}

        {/* Message Content Bubble */}
        <div className={`message-bubble ${role}`}>
          {/* Classified Intent Pill */}
          {role === "assistant" && intent && (
            <div style={{ marginBottom: "var(--space-2)" }}>
              <span className="badge badge-info" style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}>
                Intent: {intent}
              </span>
            </div>
          )}

          <div style={{ whiteSpace: "pre-wrap" }}>{content}</div>

          {/* Grounded Sources Section */}
          {role === "assistant" && sources && sources.length > 0 && (
            <div style={{ marginTop: "var(--space-3)", borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-2)" }}>
              <button
                type="button"
                onClick={() => setShowSources((prev) => !prev)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-link)",
                  fontSize: "0.75rem",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-1)",
                  padding: 0,
                }}
              >
                <span>📚</span>
                <span>{showSources ? "Hide Grounded Sources" : `View ${sources.length} Grounded Source${sources.length > 1 ? "s" : ""}`}</span>
              </button>

              {showSources && (
                <div style={{ marginTop: "var(--space-2)" }}>
                  {sources.map((src, idx) => (
                    <div key={idx} className="source-citation-badge">
                      <span>📖</span>
                      <span>
                        {src.source_name || src.title || "Clinical Guideline"}
                        {src.source_type ? ` (${src.source_type})` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Human-in-the-Loop Slot Confirmation Card */}
        {role === "assistant" && (approvalRequired || approvalStatus) && selectedSlot && (
          <HitlApprovalCard
            slot={selectedSlot}
            approvalStatus={approvalStatus}
            onApprove={onApprove}
            onReject={onReject}
            isSubmitting={isApproving}
          />
        )}

        {/* Suggested Follow-Up Prompt Chips */}
        {role === "assistant" && followUpQuestions && followUpQuestions.length > 0 && onSelectFollowUp && (
          <div className="follow-up-chips">
            {followUpQuestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                className="prompt-chip"
                onClick={() => onSelectFollowUp(q)}
              >
                ❓ {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
