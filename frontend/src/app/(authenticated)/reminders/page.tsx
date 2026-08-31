"use client";

import React from "react";
import { PlaceholderView } from "../../../components/common/PlaceholderView";

export default function RemindersPage() {
  return (
    <PlaceholderView
      title="Medication Reminders"
      icon="⏰"
      milestone="Phase 11E-4"
      description="Schedule, view, and cancel daily medication reminders and coordination notifications."
      features={[
        "Reminder creation modal with time picker (/reminders/me)",
        "Active vs. cancelled reminders list",
        "Direct reminder cancellation (/reminders/{id}/cancel)",
      ]}
    />
  );
}
