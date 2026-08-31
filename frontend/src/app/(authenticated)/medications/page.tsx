"use client";

import React from "react";
import { PlaceholderView } from "../../../components/common/PlaceholderView";

export default function MedicationsPage() {
  return (
    <PlaceholderView
      title="Active Medications"
      icon="💊"
      milestone="Phase 11E-4"
      description="View prescribed medications, dosage schedules, prescribing doctors, and clinical safety guidance."
      features={[
        "Active prescription cards with dosage and frequency (/medications/me)",
        "Non-prescribing clinical safety guidance notices",
        "Direct link to medication reminder scheduling",
      ]}
    />
  );
}
