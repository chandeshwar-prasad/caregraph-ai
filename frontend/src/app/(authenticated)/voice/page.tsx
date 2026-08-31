"use client";

import React from "react";
import { PlaceholderView } from "../../../components/common/PlaceholderView";

export default function VoicePage() {
  return (
    <PlaceholderView
      title="Voice Navigation & Assistant"
      icon="🎙️"
      milestone="Phase 11E-5"
      description="Speech-to-text audio input transcription and text-to-speech synthesized audio playback."
      features={[
        "In-browser microphone recording with Web Audio API",
        "Speech transcription endpoint integration (/voice/transcribe)",
        "Spoken audio synthesis playback stream (/voice/synthesize)",
        "Zero-disk audio retention invariant verification",
      ]}
    />
  );
}
