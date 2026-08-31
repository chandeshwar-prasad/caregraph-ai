"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "../../../../context/AuthContext";
import { apiClient, ApiClientError } from "../../../../lib/api-client";
import {
  MessagingChannel,
  MessagingSendResponse,
  MessagingOptOutResponse,
} from "../../../../types/api";

function maskPhoneNumber(phone: string): string {
  if (!phone) return "";
  const cleaned = phone.trim();
  if (cleaned.length <= 4) return "****";
  const lastFour = cleaned.slice(-4);
  const prefix = cleaned.startsWith("+1")
    ? "+1"
    : cleaned.startsWith("+91")
    ? "+91"
    : cleaned.startsWith("+")
    ? cleaned.slice(0, 3)
    : "";
  return `${prefix} ******${lastFour}`;
}

export default function AdminMessagingPage() {
  const { role } = useAuth();

  // Send Composer State
  const [channel, setChannel] = useState<MessagingChannel>("sms");
  const [recipient, setRecipient] = useState<string>("");
  const [messageBody, setMessageBody] = useState<string>("");
  const [templateName, setTemplateName] = useState<string>("");
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [sendResult, setSendResult] = useState<MessagingSendResponse | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  // Opt-Out Testing State
  const [optOutRecipient, setOptOutRecipient] = useState<string>("");
  const [optOutKeyword, setOptOutKeyword] = useState<string>("STOP");
  const [optOutChannel, setOptOutChannel] = useState<MessagingChannel>("sms");
  const [isProcessingOptOut, setIsProcessingOptOut] = useState<boolean>(false);
  const [optOutResult, setOptOutResult] = useState<MessagingOptOutResponse | null>(null);
  const [optOutError, setOptOutError] = useState<string | null>(null);

  // RBAC Access Guard
  if (role !== "admin") {
    return (
      <div className="card" style={{ maxWidth: "600px", margin: "var(--space-12) auto", textAlign: "center" }}>
        <span style={{ fontSize: "3rem", display: "block", marginBottom: "var(--space-3)" }}>🔒</span>
        <h2 style={{ color: "var(--status-emergency)", marginBottom: "var(--space-2)" }}>
          Admin Access Required
        </h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-6)" }}>
          The Outbound Messaging Gateway Console is strictly restricted to authorized administrators. Your active role (<code>{role || "guest"}</code>) is not authorized for messaging dispatch.
        </p>
        <Link href="/dashboard" className="btn btn-primary">
          ← Return to Dashboard
        </Link>
      </div>
    );
  }

  const handleOpenConfirm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipient.trim() || !messageBody.trim() || isSending) return;

    if (!recipient.trim().startsWith("+") && recipient.trim().length < 10) {
      setSendError("Please provide an E.164-compatible phone number (e.g. +12025550143).");
      return;
    }

    setSendError(null);
    setSendResult(null);
    setShowConfirmModal(true);
  };

  const handleSendMessage = async () => {
    setShowConfirmModal(false);
    setIsSending(true);
    setSendError(null);
    setSendResult(null);

    try {
      const response = await apiClient.sendMessage({
        channel,
        recipient: recipient.trim(),
        body: messageBody.trim(),
        template_name: templateName.trim() || undefined,
      });
      setSendResult(response);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (err.status === 403) {
          setSendError("Dispatch blocked: Recipient has revoked consent for automated messaging notifications (403 Forbidden).");
        } else if (err.status === 400) {
          setSendError(err.detail || "Invalid recipient format or empty message body (400 Bad Request).");
        } else {
          setSendError(err.detail || `Messaging dispatch failed (${err.status}).`);
        }
      } else {
        setSendError("Network error: Could not connect to outbound messaging gateway.");
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleOptOutSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!optOutRecipient.trim() || !optOutKeyword.trim() || isProcessingOptOut) return;

    setIsProcessingOptOut(true);
    setOptOutError(null);
    setOptOutResult(null);

    try {
      const response = await apiClient.optOutMessaging({
        channel: optOutChannel,
        recipient: optOutRecipient.trim(),
        keyword: optOutKeyword.trim(),
      });
      setOptOutResult(response);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setOptOutError(err.detail || `Opt-out processing error (${err.status}).`);
      } else {
        setOptOutError("Network error: Could not reach messaging opt-out service.");
      }
    } finally {
      setIsProcessingOptOut(false);
    }
  };

  const handleResetComposer = () => {
    setRecipient("");
    setMessageBody("");
    setTemplateName("");
    setSendResult(null);
    setSendError(null);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="card">
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-3)" }}>
          <div className="flex items-center gap-3">
            <span style={{ fontSize: "2rem" }}>📱</span>
            <div>
              <div className="flex items-center gap-2">
                <h2>Outbound Messaging Gateway Console</h2>
                <span className="badge badge-urgent">Admin Only</span>
              </div>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                Operational SMS and WhatsApp dispatch testing with recipient masking, consent enforcement, and opt-out simulation
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="badge badge-info">E.164 Masked</span>
            <span className="badge badge-success">Zero Disk Retention</span>
          </div>
        </div>

        {/* Operational / Non-Diagnostic Clinical Safety Notice */}
        <div
          style={{
            marginTop: "var(--space-3)",
            padding: "var(--space-3)",
            background: "rgba(88, 166, 255, 0.05)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            color: "var(--text-muted)",
          }}
        >
          ℹ️ <strong>Operational Communication Notice:</strong> CareGraph AI messaging is an operational communication interface for appointment alerts and care adherence reminders. It does not provide medical diagnosis, prescription adjustments, or clinical decision-making.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "var(--space-6)" }}>
        {/* Left Column: Outbound Message Composer */}
        <div className="card flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 style={{ color: "var(--brand-primary)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span>✉️</span> Message Dispatch Composer
            </h3>
            <span className="badge badge-info">{channel.toUpperCase()}</span>
          </div>

          {/* Channel Selector Tabs */}
          <div className="tab-group" style={{ marginBottom: 0 }}>
            <button
              type="button"
              className={`tab-btn ${channel === "sms" ? "active" : ""}`}
              onClick={() => setChannel("sms")}
            >
              💬 SMS Channel
            </button>
            <button
              type="button"
              className={`tab-btn ${channel === "whatsapp" ? "active" : ""}`}
              onClick={() => setChannel("whatsapp")}
            >
              📱 WhatsApp Channel
            </button>
          </div>

          <form onSubmit={handleOpenConfirm} className="flex flex-col gap-4">
            <div>
              <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                Recipient Phone Number (E.164 format)
              </label>
              <input
                type="text"
                className="input"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="+12025550143 or +919876543210"
                required
                disabled={isSending}
              />
              <span style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: "2px", display: "block" }}>
                Must include country code (e.g. +1 for US, +91 for India).
              </span>
            </div>

            <div>
              <div className="flex justify-between items-center" style={{ marginBottom: "var(--space-1)" }}>
                <label style={{ fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)" }}>
                  Message Content Body
                </label>
                <span style={{ fontSize: "0.7rem", color: messageBody.length > 1500 ? "var(--status-urgent)" : "var(--text-dim)" }}>
                  {messageBody.length} / 1600 characters
                </span>
              </div>
              <textarea
                className="input"
                rows={4}
                value={messageBody}
                onChange={(e) => setMessageBody(e.target.value)}
                maxLength={1600}
                placeholder="Type notification text (e.g. appointment confirmation or medication reminder)..."
                required
                disabled={isSending}
                style={{ resize: "vertical", fontFamily: "inherit" }}
              />
            </div>

            {/* WhatsApp Template (Optional) */}
            {channel === "whatsapp" && (
              <div>
                <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                  WhatsApp Template Name (Optional)
                </label>
                <input
                  type="text"
                  className="input"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  placeholder="e.g. appointment_reminder_v1"
                  disabled={isSending}
                />
              </div>
            )}

            {/* Quick-Fill Sample Notifications */}
            <div>
              <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", display: "block", marginBottom: "var(--space-2)" }}>
                Quick Preset Templates:
              </span>
              <div className="flex gap-2" style={{ flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="prompt-chip"
                  onClick={() => setMessageBody("CareGraph AI: Your consultation with Dr. Sarah Smith is confirmed for tomorrow at 2:00 PM. Reply STOP to opt out.")}
                >
                  📅 Appointment Confirmation
                </button>
                <button
                  type="button"
                  className="prompt-chip"
                  onClick={() => setMessageBody("CareGraph AI: Daily reminder to take your prescribed Lisinopril 10mg after breakfast. Reply STOP to unsubscribe.")}
                >
                  💊 Medication Alert
                </button>
                <button
                  type="button"
                  className="prompt-chip"
                  onClick={() => setMessageBody("CareGraph AI: Your recent physiological vitals report has been filed in your patient records. Reply STOP to end notifications.")}
                >
                  📊 Vitals Update
                </button>
              </div>
            </div>

            {/* Error Banner */}
            {sendError && (
              <div className="card" style={{ backgroundColor: "var(--status-emergency-bg)", borderColor: "var(--status-emergency-border)", padding: "var(--space-3)" }}>
                <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
                  ⚠️ {sendError}
                </p>
              </div>
            )}

            {/* Submit & Reset Controls */}
            <div className="flex items-center gap-3">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!recipient.trim() || !messageBody.trim() || isSending}
                style={{ flex: 1 }}
              >
                {isSending ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="spinner" style={{ width: "16px", height: "16px" }} />
                    <span>Transmitting Message...</span>
                  </div>
                ) : (
                  `🚀 Send ${channel.toUpperCase()} Message`
                )}
              </button>

              {(recipient || messageBody) && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleResetComposer}
                  disabled={isSending}
                  style={{ fontSize: "var(--font-size-xs)" }}
                >
                  Reset
                </button>
              )}
            </div>
          </form>

          {/* Delivery Result Card */}
          {sendResult && (
            <div className="card" style={{ background: "rgba(0, 0, 0, 0.3)", borderColor: "var(--status-success-border)", borderLeft: "4px solid var(--status-success)" }}>
              <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                <span className="badge badge-success">
                  Status: {sendResult.status.toUpperCase()}
                </span>
                <span className={sendResult.is_mock ? "badge badge-urgent" : "badge badge-info"}>
                  {sendResult.is_mock ? "Mock Provider" : "Cloud Gateway"}
                </span>
              </div>

              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div>Message ID: <code style={{ color: "var(--text-primary)" }}>{sendResult.message_id}</code></div>
                <div>Channel: <strong style={{ color: "var(--brand-primary)" }}>{sendResult.channel.toUpperCase()}</strong></div>
                <div>Provider: <strong style={{ color: "var(--text-primary)" }}>{sendResult.provider}</strong></div>
              </div>

              <p style={{ fontSize: "0.72rem", color: "var(--status-success)", margin: "var(--space-3) 0 0 0", fontWeight: 600 }}>
                ✅ Message successfully accepted and queued for carrier delivery.
              </p>
            </div>
          )}
        </div>

        {/* Right Column: Opt-Out & Compliance Simulation */}
        <div className="card flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 style={{ color: "var(--brand-primary)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span>🛡️</span> Compliance & Opt-Out Testing
            </h3>
            <span className="badge badge-info">Keyword Gateway</span>
          </div>

          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
            Simulate recipient carrier opt-out keywords (e.g. <code>STOP</code>, <code>UNSUBSCRIBE</code>, <code>CANCEL</code>) to test regulatory compliance handling.
          </p>

          <form onSubmit={handleOptOutSubmit} className="flex flex-col gap-4">
            <div>
              <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                Recipient Phone Number (E.164 format)
              </label>
              <input
                type="text"
                className="input"
                value={optOutRecipient}
                onChange={(e) => setOptOutRecipient(e.target.value)}
                placeholder="+12025550143 or +919876543210"
                required
                disabled={isProcessingOptOut}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
              <div>
                <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                  Channel
                </label>
                <select
                  className="select"
                  value={optOutChannel}
                  onChange={(e) => setOptOutChannel(e.target.value as MessagingChannel)}
                  disabled={isProcessingOptOut}
                >
                  <option value="sms">SMS</option>
                  <option value="whatsapp">WhatsApp</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                  Opt-Out Keyword
                </label>
                <select
                  className="select"
                  value={optOutKeyword}
                  onChange={(e) => setOptOutKeyword(e.target.value)}
                  disabled={isProcessingOptOut}
                >
                  <option value="STOP">STOP</option>
                  <option value="UNSUBSCRIBE">UNSUBSCRIBE</option>
                  <option value="CANCEL">CANCEL</option>
                  <option value="END">END</option>
                  <option value="QUIT">QUIT</option>
                  <option value="HELP">HELP (Non opt-out)</option>
                </select>
              </div>
            </div>

            {/* Opt-Out Error Banner */}
            {optOutError && (
              <div className="card" style={{ backgroundColor: "var(--status-emergency-bg)", borderColor: "var(--status-emergency-border)", padding: "var(--space-3)" }}>
                <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
                  ⚠️ {optOutError}
                </p>
              </div>
            )}

            <button
              type="submit"
              className="btn btn-secondary"
              disabled={!optOutRecipient.trim() || isProcessingOptOut}
            >
              {isProcessingOptOut ? "Processing Keyword..." : "🧪 Test Keyword Opt-Out"}
            </button>
          </form>

          {/* Opt-Out Result Findings */}
          {optOutResult && (
            <div className="card" style={{ background: "rgba(0, 0, 0, 0.3)", borderColor: optOutResult.opted_out ? "var(--status-emergency-border)" : "var(--border-default)" }}>
              <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                <span className={optOutResult.opted_out ? "badge badge-emergency" : "badge badge-info"}>
                  {optOutResult.opted_out ? "Recipient Opted Out" : "Keyword Processed"}
                </span>
                <span className="badge badge-neutral">
                  Channel: {optOutResult.channel.toUpperCase()}
                </span>
              </div>

              <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "4px" }}>
                <div>Keyword Matched: <strong style={{ color: optOutResult.keyword_matched ? "var(--status-success)" : "var(--status-urgent)" }}>{optOutResult.keyword_matched ? "YES" : "NO"}</strong></div>
                <div>Status: <strong style={{ color: "var(--text-primary)" }}>{optOutResult.status}</strong></div>
              </div>

              <p style={{ fontSize: "0.72rem", color: "var(--text-dim)", margin: "var(--space-3) 0 0 0" }}>
                {optOutResult.opted_out
                  ? "🔒 Recipient successfully recorded as opted out. Future automated sends to this number will be restricted."
                  : "ℹ️ Keyword did not match standard opt-out tokens; subscription status remains active."}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "var(--space-4)",
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-modal-title"
        >
          <div className="card" style={{ maxWidth: "520px", width: "100%", borderColor: "var(--brand-primary)", boxShadow: "var(--shadow-lg)" }}>
            <h3 id="confirm-modal-title" style={{ color: "var(--brand-primary)", marginBottom: "var(--space-3)" }}>
              📤 Confirm Outbound Message Dispatch
            </h3>

            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
              Please verify the transmission details before dispatching carrier notification:
            </p>

            <div style={{ background: "rgba(0, 0, 0, 0.3)", padding: "var(--space-3)", borderRadius: "var(--radius-md)", fontSize: "var(--font-size-xs)", marginBottom: "var(--space-4)" }}>
              <div style={{ marginBottom: "var(--space-2)" }}>
                <span style={{ color: "var(--text-muted)" }}>Channel: </span>
                <strong style={{ color: "var(--brand-primary)" }}>{channel.toUpperCase()}</strong>
              </div>
              <div style={{ marginBottom: "var(--space-2)" }}>
                <span style={{ color: "var(--text-muted)" }}>Masked Recipient: </span>
                <strong style={{ color: "var(--text-primary)" }}>{maskPhoneNumber(recipient)}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)" }}>Message Body: </span>
                <p style={{ color: "var(--text-primary)", fontStyle: "italic", margin: "4px 0 0 0", lineHeight: 1.5 }}>
                  &ldquo;{messageBody}&rdquo;
                </p>
              </div>
            </div>

            <p style={{ fontSize: "0.72rem", color: "var(--status-urgent)", marginBottom: "var(--space-4)" }}>
              ⚠️ Outbound transmission is subject to active patient consent verification on the server.
            </p>

            <div className="flex justify-between items-center">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowConfirmModal(false)}
                disabled={isSending}
                style={{ fontSize: "var(--font-size-xs)" }}
              >
                Cancel
              </button>

              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSendMessage}
                disabled={isSending}
                style={{ fontSize: "var(--font-size-xs)" }}
              >
                {isSending ? "Transmitting..." : "Confirm & Send"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
