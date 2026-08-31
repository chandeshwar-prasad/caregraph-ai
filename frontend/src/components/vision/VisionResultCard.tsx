"use client";

import React from "react";
import Link from "next/link";
import { VisionAnalysisResponse } from "../../types/api";

interface VisionResultCardProps {
  result: VisionAnalysisResponse;
  onClear?: () => void;
}

export const VisionResultCard: React.FC<VisionResultCardProps> = ({
  result,
  onClear,
}) => {
  const confidencePct = Math.round((result.confidence || 0) * 100);

  return (
    <div className="card flex flex-col gap-4" style={{ borderColor: "var(--brand-primary)", animation: "fadeIn 0.3s ease-out" }}>
      {/* Header */}
      <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: "var(--space-2)" }}>
        <div className="flex items-center gap-2">
          <span style={{ fontSize: "1.3rem" }}>🔍</span>
          <h3 style={{ color: "var(--brand-primary)", margin: 0 }}>
            Visual Document & Observation Findings
          </h3>
        </div>

        <div className="flex items-center gap-2">
          <span className={result.is_mock ? "badge badge-urgent" : "badge badge-success"}>
            {result.is_mock ? "Synthetic Vision Provider" : "Cloud Vision Model"}
          </span>
          {result.media_type && (
            <span className="badge badge-info" style={{ fontSize: "0.7rem" }}>
              {result.media_type.toUpperCase()}
            </span>
          )}
        </div>
      </div>

      {/* Mandatory Non-Diagnostic Clinical Disclaimer */}
      <div
        className="card"
        style={{
          backgroundColor: "var(--status-urgent-bg)",
          borderColor: "var(--status-urgent-border)",
          padding: "var(--space-3)",
          margin: 0,
        }}
        role="alert"
      >
        <p style={{ color: "var(--status-urgent)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
          ⚠️ {result.clinical_disclaimer || "CareGraph AI Vision is for care navigation and document observation assistance only, and does not provide clinical diagnosis or medical evaluation."}
        </p>
      </div>

      {/* Structured Observational Description */}
      <div>
        <h4 style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase", marginBottom: "var(--space-1)" }}>
          Observational Description
        </h4>
        <blockquote
          style={{
            background: "rgba(0, 0, 0, 0.25)",
            borderLeft: "3px solid var(--brand-primary)",
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-sm)",
            color: "var(--text-primary)",
            margin: 0,
            lineHeight: 1.6,
          }}
        >
          {result.description}
        </blockquote>
      </div>

      {/* Detected Visual Features */}
      {result.detected_features && result.detected_features.length > 0 && (
        <div>
          <h4 style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase", marginBottom: "var(--space-2)" }}>
            Detected Document & Clinical Entities ({result.detected_features.length})
          </h4>
          <div className="flex gap-2" style={{ flexWrap: "wrap" }}>
            {result.detected_features.map((feat, idx) => (
              <span key={idx} className="vision-feature-pill">
                🏷️ {feat}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Metrics & Confidence */}
      <div style={{ background: "rgba(0, 0, 0, 0.2)", padding: "var(--space-3)", borderRadius: "var(--radius-md)" }}>
        <div className="flex items-center justify-between" style={{ fontSize: "var(--font-size-xs)", marginBottom: "var(--space-1)" }}>
          <span style={{ color: "var(--text-muted)" }}>Observation Confidence</span>
          <strong style={{ color: "var(--text-primary)" }}>{confidencePct}%</strong>
        </div>
        <div className="confidence-bar-bg" aria-label={`Confidence: ${confidencePct}%`}>
          <div className="confidence-bar-fill" style={{ width: `${confidencePct}%` }} />
        </div>

        {(result.width || result.height) && (
          <div style={{ marginTop: "var(--space-2)", fontSize: "0.7rem", color: "var(--text-dim)" }}>
            Dimensions: {result.width} × {result.height} px
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-3)", flexWrap: "wrap", gap: "var(--space-2)" }}>
        {onClear && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClear}
            style={{ fontSize: "var(--font-size-xs)", padding: "0.35rem 0.75rem" }}
          >
            🔄 Analyze Another Image
          </button>
        )}

        <Link
          href="/chat"
          className="btn btn-primary"
          style={{ fontSize: "var(--font-size-xs)", padding: "0.35rem 0.75rem" }}
        >
          💬 Discuss Findings in Chat →
        </Link>
      </div>
    </div>
  );
};
