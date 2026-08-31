"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { apiClient, ApiClientError } from "../../../lib/api-client";
import { VoiceTranscriptionResponse } from "../../../types/api";

export default function VoicePage() {
  // STT State
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordDuration, setRecordDuration] = useState<number>(0);
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [transcriptionResult, setTranscriptionResult] = useState<VoiceTranscriptionResponse | null>(null);
  const [sttError, setSttError] = useState<string | null>(null);
  const [copiedTranscript, setCopiedTranscript] = useState<boolean>(false);

  // TTS State
  const [ttsText, setTtsText] = useState<string>(
    "Hello! I am your CareGraph AI care coordinator. How can I assist you with your health navigation today?"
  );
  const [isSynthesizing, setIsSynthesizing] = useState<boolean>(false);
  const [ttsAudioUrl, setTtsAudioUrl] = useState<string | null>(null);
  const [ttsError, setTtsError] = useState<string | null>(null);

  // Refs for audio streams & recording
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  // Cleanup Object URL on unmount or URL change
  useEffect(() => {
    return () => {
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const handleStartRecording = async () => {
    setSttError(null);
    setTranscriptionResult(null);
    audioChunksRef.current = [];

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setSttError("Microphone recording is not supported in this browser. Please use the audio file upload option.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/ogg")
        ? "audio/ogg"
        : "audio/wav";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        if (audioBlob.size > 0) {
          await processAudioForTranscription(audioBlob, `recording.${mimeType.split("/")[1] || "webm"}`);
        }
      };

      mediaRecorder.start(250); // Slice chunks every 250ms
      setIsRecording(true);
      setRecordDuration(0);

      timerIntervalRef.current = setInterval(() => {
        setRecordDuration((prev) => prev + 1);
      }, 1000);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "NotAllowedError") {
        setSttError("Microphone access was denied. Please allow microphone permissions in your browser.");
      } else {
        setSttError("Could not access microphone. Please check your audio input settings.");
      }
    }
  };

  const handleStopRecording = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      setSttError("Audio file exceeds the 10MB limit. Please choose a smaller audio clip.");
      return;
    }

    setSttError(null);
    setTranscriptionResult(null);
    await processAudioForTranscription(file, file.name);
  };

  const processAudioForTranscription = async (blob: Blob, filename: string) => {
    setIsTranscribing(true);
    setSttError(null);
    try {
      const result = await apiClient.transcribeAudio(blob, filename);
      setTranscriptionResult(result);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setSttError(err.detail || "Audio transcription failed.");
      } else {
        setSttError("Network error: Could not reach speech transcription service.");
      }
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleSynthesize = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ttsText.trim()) return;

    setIsSynthesizing(true);
    setTtsError(null);

    // Revoke previous URL if exists
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
      setTtsAudioUrl(null);
    }

    try {
      const audioBlob = await apiClient.synthesizeSpeech({
        text: ttsText.trim(),
      });

      const newUrl = URL.createObjectURL(audioBlob);
      audioUrlRef.current = newUrl;
      setTtsAudioUrl(newUrl);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setTtsError(err.detail || "Text-to-speech synthesis failed.");
      } else {
        setTtsError("Network error during speech synthesis.");
      }
    } finally {
      setIsSynthesizing(false);
    }
  };

  const handleCopyTranscript = () => {
    if (transcriptionResult?.transcript) {
      navigator.clipboard.writeText(transcriptionResult.transcript);
      setCopiedTranscript(true);
      setTimeout(() => setCopiedTranscript(false), 2000);
    }
  };

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="card">
        <div className="flex items-center gap-3" style={{ marginBottom: "var(--space-2)" }}>
          <span style={{ fontSize: "2rem" }}>🎙️</span>
          <div>
            <h2>Voice Navigation & Synthesis Suite</h2>
            <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              In-memory Speech-to-Text (STT) transcription and Text-to-Speech (TTS) audio synthesis
            </p>
          </div>
        </div>

        {/* Clinical Safety Disclaimer */}
        <div
          style={{
            marginTop: "var(--space-3)",
            padding: "var(--space-3)",
            background: "rgba(88, 166, 255, 0.05)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            color: "var(--text-muted)",
          }}
        >
          ℹ️ <strong>Assistive Navigation Interface:</strong> Voice transcription and speech synthesis are accessibility and care-coordination interfaces. They do not perform autonomous medical diagnosis or clinical assessment.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "var(--space-6)" }}>
        {/* Section 1: Speech-to-Text Audio Input */}
        <div className="card flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 style={{ color: "var(--brand-primary)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span>🗣️</span> Speech-to-Text Input
            </h3>
            <span className="badge badge-info">Zero Disk Retention</span>
          </div>

          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
            Record speech using your microphone or select an existing audio clip for in-memory transcription.
          </p>

          {/* Record Control Box */}
          <div className="record-btn-container">
            <button
              type="button"
              className={`record-btn ${isRecording ? "recording" : ""}`}
              onClick={isRecording ? handleStopRecording : handleStartRecording}
              disabled={isTranscribing}
              aria-label={isRecording ? "Stop voice recording" : "Start voice recording"}
            >
              {isRecording ? "⏹️" : "🎙️"}
            </button>

            <div style={{ marginTop: "var(--space-3)", textAlign: "center" }}>
              {isRecording ? (
                <div className="flex items-center gap-2">
                  <span style={{ color: "var(--status-emergency)", fontWeight: 700, fontSize: "var(--font-size-sm)" }}>
                    ● Recording ({formatTimer(recordDuration)})
                  </span>
                </div>
              ) : isTranscribing ? (
                <div className="flex items-center gap-2" style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
                  <div className="spinner" style={{ width: "14px", height: "14px" }} />
                  <span>Transcribing speech in memory...</span>
                </div>
              ) : (
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                  Click to speak (English / Multilingual)
                </span>
              )}
            </div>
          </div>

          {/* Audio Upload Fallback */}
          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-3)" }}>
            <label style={{ display: "block", fontSize: "var(--font-size-xs)", color: "var(--text-dim)", marginBottom: "var(--space-2)" }}>
              📁 Or upload pre-recorded audio (WAV, MP3, WEBM, OGG — max 10MB):
            </label>
            <input
              type="file"
              accept="audio/*"
              className="input"
              onChange={handleFileUpload}
              disabled={isRecording || isTranscribing}
              style={{ fontSize: "var(--font-size-xs)", padding: "var(--space-2)" }}
            />
          </div>

          {/* STT Error Banner */}
          {sttError && (
            <div className="card" style={{ backgroundColor: "var(--status-emergency-bg)", borderColor: "var(--status-emergency-border)", padding: "var(--space-3)" }}>
              <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
                ⚠️ {sttError}
              </p>
            </div>
          )}

          {/* Transcription Results */}
          {transcriptionResult && (
            <div className="card" style={{ background: "rgba(0, 0, 0, 0.3)", borderColor: "var(--brand-primary)" }}>
              <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-2)" }}>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 600 }}>
                  Transcription Output
                </span>
                <span className={transcriptionResult.is_mock ? "badge badge-urgent" : "badge badge-success"}>
                  {transcriptionResult.is_mock ? "Mock Provider" : "Cloud STT"}
                </span>
              </div>

              <blockquote style={{ fontSize: "var(--font-size-sm)", color: "var(--text-primary)", fontStyle: "italic", margin: "var(--space-2) 0", lineHeight: 1.6 }}>
                &ldquo;{transcriptionResult.transcript}&rdquo;
              </blockquote>

              <div className="flex items-center justify-between" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-3)", marginTop: "var(--space-3)", flexWrap: "wrap", gap: "var(--space-2)" }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>
                  Language: <strong>{transcriptionResult.detected_language}</strong>
                  {transcriptionResult.duration_seconds > 0 && ` • Duration: ${transcriptionResult.duration_seconds.toFixed(1)}s`}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleCopyTranscript}
                    style={{ fontSize: "0.7rem", padding: "0.25rem 0.5rem" }}
                  >
                    {copiedTranscript ? "✅ Copied!" : "📋 Copy"}
                  </button>

                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setTtsText(transcriptionResult.transcript)}
                    style={{ fontSize: "0.7rem", padding: "0.25rem 0.5rem" }}
                  >
                    🔊 Read Aloud
                  </button>

                  <Link
                    href="/chat"
                    className="btn btn-primary"
                    style={{ fontSize: "0.7rem", padding: "0.25rem 0.5rem" }}
                  >
                    💬 Ask Care Coordinator →
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 2: Text-to-Speech Audio Synthesis */}
        <div className="card flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 style={{ color: "var(--brand-primary)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span>🔊</span> Text-to-Speech Synthesis
            </h3>
            <span className="badge badge-info">WAV Audio Stream</span>
          </div>

          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
            Synthesize care instructions, clinical notices, or conversational guidance into spoken audio.
          </p>

          <form onSubmit={handleSynthesize} className="flex flex-col gap-3">
            <div>
              <label style={{ display: "block", fontSize: "var(--font-size-xs)", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
                Text to Synthesize ({ttsText.length} / 4000 characters)
              </label>
              <textarea
                className="input"
                rows={4}
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                maxLength={4000}
                placeholder="Enter text for the coordinator to speak..."
                required
                disabled={isSynthesizing}
                style={{ resize: "vertical", fontFamily: "inherit" }}
              />
            </div>

            {/* Quick-Prompt Samples */}
            <div className="flex gap-2" style={{ flexWrap: "wrap" }}>
              <button
                type="button"
                className="prompt-chip"
                onClick={() => setTtsText("Your appointment with Dr. Sarah Smith is scheduled for tomorrow at 2:00 PM.")}
              >
                📅 Appointment Reminder
              </button>
              <button
                type="button"
                className="prompt-chip"
                onClick={() => setTtsText("Please take your Lisinopril 10 milligram prescription with water after breakfast.")}
              >
                💊 Medication Direction
              </button>
              <button
                type="button"
                className="prompt-chip"
                onClick={() => setTtsText("If you experience chest pain or severe shortness of breath, please call 911 immediately.")}
              >
                🚨 Emergency Notice
              </button>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSynthesizing || !ttsText.trim()}
              style={{ marginTop: "var(--space-2)" }}
            >
              {isSynthesizing ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="spinner" style={{ width: "16px", height: "16px" }} />
                  <span>Synthesizing Audio Stream...</span>
                </div>
              ) : (
                "🔊 Generate Speech Audio"
              )}
            </button>
          </form>

          {/* TTS Error Alert */}
          {ttsError && (
            <div className="card" style={{ backgroundColor: "var(--status-emergency-bg)", borderColor: "var(--status-emergency-border)", padding: "var(--space-3)" }}>
              <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
                ⚠️ {ttsError}
              </p>
            </div>
          )}

          {/* Playback Audio Stream */}
          {ttsAudioUrl && (
            <div className="audio-player-wrapper">
              <div className="flex items-center justify-between" style={{ marginBottom: "var(--space-1)" }}>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--brand-primary)", fontWeight: 600 }}>
                  ▶️ Audio Playback Stream (WAV)
                </span>
                <span className="badge badge-success" style={{ fontSize: "0.65rem" }}>
                  Active Stream
                </span>
              </div>
              <audio controls autoPlay src={ttsAudioUrl}>
                Your browser does not support HTML5 audio playback.
              </audio>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
