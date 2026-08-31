"use client";

import React from "react";
import { PlaceholderView } from "../../../components/common/PlaceholderView";

export default function ChatPage() {
  return (
    <PlaceholderView
      title="AI Care Coordination Chat"
      icon="💬"
      milestone="Phase 11E-3"
      description="Interactive multi-agent conversation interface with LangGraph orchestration, deterministic safety screening, and Human-in-the-Loop appointment scheduling."
      features={[
        "Real-time LangGraph chat thread session management",
        "Deterministic red-flag safety escalation alert cards",
        "Grounded medical guideline citations & source attribution",
        "Human-in-the-Loop (HITL) slot confirmation and booking cards (/chat/approve)",
        "Suggested clinical screening follow-up questions",
      ]}
    />
  );
}
