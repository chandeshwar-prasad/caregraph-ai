"use client";

import React from "react";
import Link from "next/link";

interface PlaceholderViewProps {
  title: string;
  icon: string;
  milestone: string;
  description: string;
  features: string[];
}

export const PlaceholderView: React.FC<PlaceholderViewProps> = ({
  title,
  icon,
  milestone,
  description,
  features,
}) => {
  return (
    <div style={{ maxWidth: "720px", margin: "0 auto" }}>
      <div className="card">
        <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-4)" }}>
          <div className="flex items-center gap-3">
            <span style={{ fontSize: "2rem" }}>{icon}</span>
            <div>
              <h2>{title}</h2>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                Roadmap Component
              </p>
            </div>
          </div>
          <span className="badge badge-info">{milestone}</span>
        </div>

        <p style={{ marginBottom: "var(--space-4)", fontSize: "var(--font-size-sm)" }}>
          {description}
        </p>

        <div
          style={{
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            padding: "var(--space-4)",
            marginBottom: "var(--space-6)",
          }}
        >
          <h4 style={{ fontSize: "var(--font-size-sm)", color: "var(--brand-primary)", marginBottom: "var(--space-2)" }}>
            Planned Capabilities in {milestone}:
          </h4>
          <ul style={{ paddingLeft: "var(--space-5)", color: "var(--text-secondary)", fontSize: "var(--font-size-xs)" }}>
            {features.map((feat, idx) => (
              <li key={idx} style={{ marginBottom: "var(--space-1)" }}>
                {feat}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center justify-between">
          <Link href="/dashboard" className="btn btn-secondary" style={{ fontSize: "var(--font-size-xs)" }}>
            ← Back to Dashboard
          </Link>
          <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)" }}>
            FastAPI Backend Endpoints Ready
          </span>
        </div>
      </div>
    </div>
  );
};
