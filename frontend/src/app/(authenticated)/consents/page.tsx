"use client";

import React from "react";
import { PlaceholderView } from "../../../components/common/PlaceholderView";

export default function ConsentsPage() {
  return (
    <PlaceholderView
      title="Consent Center"
      icon="🛡️"
      milestone="Phase 11E-4"
      description="Manage explicit patient privacy consent for AI processing, vital tracking, and appointment booking."
      features={[
        "Active consent types status table (/consents/me)",
        "Granular consent grant toggle (/consents/me/grant)",
        "Granular consent revocation toggle (/consents/me/revoke)",
        "Expiration dates and policy version tracking",
      ]}
    />
  );
}
