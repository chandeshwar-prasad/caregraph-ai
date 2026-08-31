"use client";

import React, { useState, useEffect, useRef } from "react";
import { apiClient, ApiClientError } from "../../../lib/api-client";
import { VisionAnalysisResponse } from "../../../types/api";
import { VisionResultCard } from "../../../components/vision/VisionResultCard";

const SUPPORTED_MIME_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"];
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

export default function VisionPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<VisionAnalysisResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const previewUrlRef = useRef<string | null>(null);

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = null;
      }
    };
  }, []);

  const handleFileSelection = (file: File | null) => {
    setErrorMessage(null);
    setAnalysisResult(null);

    if (!file) return;

    // MIME Validation
    if (!SUPPORTED_MIME_TYPES.includes(file.type.toLowerCase())) {
      setErrorMessage(`Unsupported image format (${file.type || "unknown"}). Please upload a PNG, JPEG, WEBP, or GIF.`);
      return;
    }

    // Size Validation (10MB)
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      setErrorMessage(`Image exceeds maximum allowable size (10MB). Selected file is ${(file.size / (1024 * 1024)).toFixed(1)}MB.`);
      return;
    }

    if (file.size <= 0) {
      setErrorMessage("The selected image file is empty.");
      return;
    }

    // Revoke previous preview URL
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }

    const newUrl = URL.createObjectURL(file);
    previewUrlRef.current = newUrl;
    setPreviewUrl(newUrl);
    setSelectedFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileSelection(file);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || isAnalyzing) return;

    setIsAnalyzing(true);
    setErrorMessage(null);

    try {
      const response = await apiClient.analyzeImage(selectedFile, selectedFile.name);
      setAnalysisResult(response);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.detail || "Image analysis failed.");
      } else {
        setErrorMessage("Network error: Could not reach the Vision analysis service.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleReset = () => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setAnalysisResult(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="card">
        <div className="flex items-center gap-3" style={{ marginBottom: "var(--space-2)" }}>
          <span style={{ fontSize: "2rem" }}>👁️</span>
          <div>
            <h2>Vision Document Analyzer</h2>
            <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              In-memory visual entity extraction and document observation assistance
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
          ℹ️ <strong>Assistive Document Observation Only:</strong> Vision analysis is provided for care navigation and document observation assistance. It does not perform autonomous medical diagnosis or clinical interpretation.
        </div>
      </div>

      {/* Main Grid: Upload & Observation Findings */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "var(--space-6)" }}>
        {/* Upload & Preview Card */}
        <div className="card flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 style={{ color: "var(--brand-primary)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <span>📤</span> Image Upload & Inspection
            </h3>
            <span className="badge badge-info">Zero Disk Retention</span>
          </div>

          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-secondary)" }}>
            Select or drop a medical document, medication label, or clinical record for in-memory entity extraction.
          </p>

          {/* Dropzone */}
          {!previewUrl ? (
            <div
              className={`vision-dropzone ${isDragOver ? "dragover" : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
              aria-label="Upload document image"
            >
              <span style={{ fontSize: "2.5rem", marginBottom: "var(--space-2)" }}>📸</span>
              <h4 style={{ color: "var(--text-primary)", marginBottom: "var(--space-1)" }}>
                Drag & drop image here or click to browse
              </h4>
              <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                Supports PNG, JPEG, WEBP, GIF (up to 10MB)
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp,image/gif"
                style={{ display: "none" }}
                onChange={(e) => handleFileSelection(e.target.files?.[0] || null)}
              />
            </div>
          ) : (
            /* Local Preview */
            <div className="vision-preview-container">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewUrl}
                alt="Selected preview"
                className="vision-preview-image"
              />

              <div style={{ marginTop: "var(--space-3)", textAlign: "center", width: "100%" }}>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-primary)", fontWeight: 600 }}>
                  📄 {selectedFile?.name}
                </span>
                <span style={{ fontSize: "0.7rem", color: "var(--text-dim)", display: "block" }}>
                  {(selectedFile?.size ? (selectedFile.size / 1024).toFixed(1) : 0)} KB • {selectedFile?.type}
                </span>
              </div>
            </div>
          )}

          {/* Error Banner */}
          {errorMessage && (
            <div className="card" style={{ backgroundColor: "var(--status-emergency-bg)", borderColor: "var(--status-emergency-border)", padding: "var(--space-3)" }}>
              <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
                ⚠️ {errorMessage}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleAnalyze}
              disabled={!selectedFile || isAnalyzing}
              style={{ flex: 1 }}
            >
              {isAnalyzing ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="spinner" style={{ width: "16px", height: "16px" }} />
                  <span>Analyzing Visual Entities...</span>
                </div>
              ) : (
                "🔍 Analyze Document Image"
              )}
            </button>

            {selectedFile && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleReset}
                disabled={isAnalyzing}
                style={{ fontSize: "var(--font-size-xs)" }}
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Observation Results Card */}
        <div>
          {analysisResult ? (
            <VisionResultCard
              result={analysisResult}
              onClear={handleReset}
            />
          ) : (
            <div className="card" style={{ textAlign: "center", padding: "var(--space-12) var(--space-6)" }}>
              <span style={{ fontSize: "3rem", display: "block", marginBottom: "var(--space-3)" }}>🩺</span>
              <h3 style={{ marginBottom: "var(--space-2)" }}>No Image Analyzed</h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", maxWidth: "400px", margin: "0 auto" }}>
                Upload a document or photo on the left to extract structured clinical features and text observations.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
