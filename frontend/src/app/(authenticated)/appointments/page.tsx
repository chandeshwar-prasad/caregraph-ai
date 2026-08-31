"use client";

import React from "react";
import { PlaceholderView } from "../../../components/common/PlaceholderView";

export default function AppointmentsPage() {
  return (
    <PlaceholderView
      title="My Appointments"
      icon="📅"
      milestone="Phase 11E-4"
      description="Scheduled consultation calendar, status tracking, and cancellation controls for doctor visits."
      features={[
        "Active vs. cancelled appointment status breakdown",
        "Doctor, specialty, and time slot details cards",
        "Direct appointment cancellation trigger (/appointments/{id}/cancel)",
        "Mock consultation provider disclaimer notices",
      ]}
    />
  );
}
