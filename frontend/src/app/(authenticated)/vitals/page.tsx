"use client";

import React from "react";
import { PlaceholderView } from "../../../components/common/PlaceholderView";

export default function VitalsPage() {
  return (
    <PlaceholderView
      title="Vitals Sign Tracker"
      icon="❤️"
      milestone="Phase 11E-4"
      description="Track, log, and view vital sign trends including blood pressure, heart rate, weight, temperature, and SpO2."
      features={[
        "Vital recording form with measurement unit validation (/vitals/me)",
        "Historical readings data table with type filters",
        "Clinical safety reference disclaimer banners",
      ]}
    />
  );
}
