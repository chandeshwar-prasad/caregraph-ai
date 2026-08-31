"use client";

import React from "react";
import { PlaceholderView } from "../../../components/common/PlaceholderView";

export default function VisionPage() {
  return (
    <PlaceholderView
      title="Vision Document Analyzer"
      icon="👁️"
      milestone="Phase 11E-5"
      description="Visual document inspection and structured entity extraction for healthcare coordination."
      features={[
        "Drag-and-drop file uploader with PNG/JPEG preview",
        "Document vision analysis endpoint (/vision/analyze)",
        "Structured entity extraction and confidence score display",
        "Mandatory clinical non-diagnostic disclaimer verification",
      ]}
    />
  );
}
