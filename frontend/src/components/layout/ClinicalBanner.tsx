"use client";

import React from "react";

export const ClinicalBanner: React.FC = () => {
  return (
    <aside className="clinical-disclaimer-banner" aria-label="Clinical safety disclaimer">
      <span role="img" aria-hidden="true">ℹ️</span>
      <span>
        <strong>CareGraph AI Navigation Assistant:</strong> Synthetic demonstration system. Not an AI doctor and not a substitute for clinical judgment. For emergencies, call <strong>911 / 112</strong> immediately.
      </span>
    </aside>
  );
};
