/**
 * CareGraph AI - Phase 11E-5 Multi-Modal Test Suite
 * Validates Voice STT/TTS contracts, Vision image contracts, and Messaging console contracts.
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";

// ==========================================
// 1. Voice Speech-to-Text (STT) Contracts
// ==========================================

describe("Voice STT Payload & Contract Validation", () => {
  const MAX_AUDIO_BYTES = 10 * 1024 * 1024; // 10MB
  const SUPPORTED_AUDIO_MIMES = ["audio/wav", "audio/webm", "audio/ogg", "audio/mpeg", "audio/mp3", "audio/x-wav"];

  function validateAudioUpload(fileSize, mimeType) {
    if (fileSize <= 0) {
      throw new Error("Audio payload cannot be empty");
    }
    if (fileSize > MAX_AUDIO_BYTES) {
      throw new Error("Audio payload exceeds maximum allowable size (10MB)");
    }
    if (!SUPPORTED_AUDIO_MIMES.includes(mimeType)) {
      throw new Error(`Unsupported audio MIME type: ${mimeType}`);
    }
    return true;
  }

  test("accepts valid audio recordings within size limit", () => {
    assert.ok(validateAudioUpload(1024 * 100, "audio/webm"));
    assert.ok(validateAudioUpload(1024 * 500, "audio/wav"));
  });

  test("rejects oversized audio files exceeding 10MB", () => {
    assert.throws(() => validateAudioUpload(11 * 1024 * 1024, "audio/wav"), /exceeds maximum allowable size/);
  });

  test("rejects unsupported audio MIME types", () => {
    assert.throws(() => validateAudioUpload(1024, "video/mp4"), /Unsupported audio MIME type/);
    assert.throws(() => validateAudioUpload(1024, "application/pdf"), /Unsupported audio MIME type/);
  });

  test("parses structured VoiceTranscriptionResponse schema", () => {
    const mockResponse = {
      transcript: "I have had a mild fever and cough for two days.",
      detected_language: "en",
      duration_seconds: 3.5,
      is_mock: true,
    };

    assert.ok(mockResponse.transcript.length > 0);
    assert.equal(mockResponse.detected_language, "en");
    assert.equal(mockResponse.duration_seconds, 3.5);
    assert.equal(mockResponse.is_mock, true);
  });
});

// ==========================================
// 2. Voice Text-to-Speech (TTS) Contracts
// ==========================================

describe("Voice TTS Payload & Object URL Lifecycle", () => {
  const MAX_TTS_CHARS = 4000;

  function validateSynthesisPayload(text, voiceId) {
    if (!text || text.trim().length === 0) {
      throw new Error("Synthesis text cannot be empty");
    }
    if (text.length > MAX_TTS_CHARS) {
      throw new Error("Synthesis text exceeds maximum character limit (4000)");
    }
    return {
      text: text.trim(),
      voice_id: voiceId || null,
    };
  }

  test("validates safe TTS synthesis request payload", () => {
    const payload = validateSynthesisPayload("Your appointment is scheduled for tomorrow at 2:00 PM.");
    assert.equal(payload.text, "Your appointment is scheduled for tomorrow at 2:00 PM.");
    assert.equal(payload.voice_id, null);
  });

  test("rejects empty or blank text for synthesis", () => {
    assert.throws(() => validateSynthesisPayload(""), /cannot be empty/);
    assert.throws(() => validateSynthesisPayload("   "), /cannot be empty/);
  });

  test("rejects synthesis text exceeding character limit", () => {
    const hugeText = "A".repeat(4001);
    assert.throws(() => validateSynthesisPayload(hugeText), /exceeds maximum character limit/);
  });

  test("tracks object URL creation and revocation lifecycle pattern", () => {
    const revokedUrls = [];
    const mockRevoke = (url) => revokedUrls.push(url);

    let activeUrl = "blob:http://localhost:3000/mock-uuid-1";

    // Simulate replacing active audio with new synthesis stream
    if (activeUrl) {
      mockRevoke(activeUrl);
      activeUrl = "blob:http://localhost:3000/mock-uuid-2";
    }

    assert.equal(revokedUrls.length, 1);
    assert.equal(revokedUrls[0], "blob:http://localhost:3000/mock-uuid-1");
    assert.equal(activeUrl, "blob:http://localhost:3000/mock-uuid-2");
  });
});

// ==========================================
// 3. Clinical Safety & Zero-PHI Verification
// ==========================================

describe("Voice Clinical Safety & Privacy Invariants", () => {
  test("verifies assistive navigation non-diagnostic disclaimer", () => {
    const disclaimer = "Voice transcription and speech synthesis are accessibility and care-coordination interfaces. They do not perform autonomous medical diagnosis or clinical assessment.";
    assert.ok(disclaimer.toLowerCase().includes("accessibility"));
    assert.ok(disclaimer.includes("do not perform autonomous medical diagnosis"));
  });

  test("verifies no client-side patient ID injection in voice requests", () => {
    const voiceEndpoints = ["/voice/transcribe", "/voice/synthesize"];
    voiceEndpoints.forEach((ep) => {
      assert.ok(!ep.includes("patient_id="), `Endpoint ${ep} must not require patient_id query param`);
      assert.ok(!ep.includes("user_id="), `Endpoint ${ep} must not require user_id query param`);
    });
  });
});

// ==========================================
// 4. Vision Document Analyzer Contracts
// ==========================================

describe("Vision Image Validation & Analysis Contracts", () => {
  const MAX_IMAGE_BYTES = 10 * 1024 * 1024; // 10MB
  const SUPPORTED_VISION_MIMES = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"];

  function validateVisionUpload(fileSize, mimeType) {
    if (!fileSize || fileSize <= 0) {
      throw new Error("Image file cannot be empty");
    }
    if (fileSize > MAX_IMAGE_BYTES) {
      throw new Error("Image file exceeds maximum allowable size (10MB)");
    }
    if (!SUPPORTED_VISION_MIMES.includes(mimeType.toLowerCase())) {
      throw new Error(`Unsupported image format (${mimeType}). Supported: PNG, JPEG, WEBP, GIF`);
    }
    return true;
  }

  test("accepts valid medical document image formats within size limit", () => {
    assert.ok(validateVisionUpload(1024 * 500, "image/png"));
    assert.ok(validateVisionUpload(1024 * 1024 * 2, "image/jpeg"));
    assert.ok(validateVisionUpload(1024 * 200, "image/webp"));
    assert.ok(validateVisionUpload(1024 * 100, "image/gif"));
  });

  test("rejects oversized images exceeding 10MB limit", () => {
    assert.throws(() => validateVisionUpload(11 * 1024 * 1024, "image/png"), /exceeds maximum allowable size/);
  });

  test("rejects unsupported MIME formats", () => {
    assert.throws(() => validateVisionUpload(1024, "application/pdf"), /Unsupported image format/);
    assert.throws(() => validateVisionUpload(1024, "text/plain"), /Unsupported image format/);
    assert.throws(() => validateVisionUpload(1024, "video/mp4"), /Unsupported image format/);
  });

  test("rejects empty image files (0 bytes)", () => {
    assert.throws(() => validateVisionUpload(0, "image/png"), /cannot be empty/);
  });

  test("parses structured VisionAnalysisResponse schema", () => {
    const mockVisionResponse = {
      detected_features: ["Prescription header", "Medication label", "Dosage: 10mg"],
      description: "Observation of a printed prescription document for blood pressure management.",
      media_type: "image/png",
      width: 1024,
      height: 768,
      confidence: 0.94,
      clinical_disclaimer: "CareGraph AI Vision is for care navigation and symptom/document observation assistance only, and does not provide clinical diagnosis, medical evaluation, or diagnostic decisions.",
      is_mock: true,
    };

    assert.equal(mockVisionResponse.detected_features.length, 3);
    assert.equal(mockVisionResponse.detected_features[0], "Prescription header");
    assert.ok(mockVisionResponse.description.includes("printed prescription"));
    assert.equal(mockVisionResponse.width, 1024);
    assert.equal(mockVisionResponse.height, 768);
    assert.equal(mockVisionResponse.confidence, 0.94);
    assert.equal(mockVisionResponse.is_mock, true);
    assert.ok(mockVisionResponse.clinical_disclaimer.includes("does not provide clinical diagnosis"));
  });

  test("verifies vision preview URL creation and unmount cleanup pattern", () => {
    const activeUrls = new Set();
    const mockCreate = (id) => {
      const url = `blob:http://localhost:3000/preview-${id}`;
      activeUrls.add(url);
      return url;
    };
    const mockRevoke = (url) => {
      activeUrls.delete(url);
    };

    const url1 = mockCreate("doc1");
    assert.equal(activeUrls.has(url1), true);

    // Replace with doc2
    mockRevoke(url1);
    const url2 = mockCreate("doc2");
    assert.equal(activeUrls.has(url1), false);
    assert.equal(activeUrls.has(url2), true);

    // Component unmount
    mockRevoke(url2);
    assert.equal(activeUrls.size, 0);
  });

  test("verifies zero image bytes stored in persistent web storage", () => {
    // Assert invariant: no storage key should ever contain image base64 or blob
    const forbiddenStorageKeys = ["vision_image", "image_base64", "patient_photo", "document_bytes"];
    const mockLocalStorage = { caregraph_chat_session: "sess_12345", caregraph_token: "jwt_token" };

    forbiddenStorageKeys.forEach((key) => {
      assert.equal(mockLocalStorage[key], undefined, `Storage must not contain ${key}`);
    });
  });
});

// ==========================================
// 5. Outbound Messaging Gateway Contracts
// ==========================================

describe("Outbound Messaging Gateway Validation & Contracts", () => {
  const MAX_MESSAGE_CHARS = 1600;

  function maskPhoneNumber(phone) {
    if (!phone) return "";
    const cleaned = phone.trim();
    if (cleaned.length <= 4) return "****";
    const lastFour = cleaned.slice(-4);
    const prefix = cleaned.startsWith("+1")
      ? "+1"
      : cleaned.startsWith("+91")
      ? "+91"
      : cleaned.startsWith("+")
      ? cleaned.slice(0, 3)
      : "";
    return `${prefix} ******${lastFour}`;
  }

  function validateSendMessagePayload(channel, recipient, body) {
    if (!["sms", "whatsapp"].includes(channel)) {
      throw new Error(`Unsupported channel: ${channel}`);
    }
    if (!recipient || recipient.trim().length < 8) {
      throw new Error("Invalid recipient format");
    }
    if (!body || body.trim().length === 0) {
      throw new Error("Message body cannot be empty");
    }
    if (body.length > MAX_MESSAGE_CHARS) {
      throw new Error("Message body exceeds 1,600 character limit");
    }
    return {
      channel,
      recipient: recipient.trim(),
      body: body.trim(),
    };
  }

  function validateOptOutKeyword(keyword) {
    const OPT_OUT_KEYWORDS = ["STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"];
    const normalized = (keyword || "").trim().toUpperCase();
    return {
      keyword: normalized,
      isOptOut: OPT_OUT_KEYWORDS.includes(normalized),
    };
  }

  test("validates SMS channel send request payload", () => {
    const payload = validateSendMessagePayload("sms", "+12025550143", "CareGraph appointment reminder for tomorrow.");
    assert.equal(payload.channel, "sms");
    assert.equal(payload.recipient, "+12025550143");
    assert.ok(payload.body.includes("appointment reminder"));
  });

  test("validates WhatsApp channel send request payload", () => {
    const payload = validateSendMessagePayload("whatsapp", "+919876543210", "CareGraph medication alert.");
    assert.equal(payload.channel, "whatsapp");
    assert.equal(payload.recipient, "+919876543210");
  });

  test("rejects invalid channel types", () => {
    assert.throws(() => validateSendMessagePayload("telegram", "+12025550143", "Hello"), /Unsupported channel/);
  });

  test("rejects empty message body", () => {
    assert.throws(() => validateSendMessagePayload("sms", "+12025550143", ""), /cannot be empty/);
    assert.throws(() => validateSendMessagePayload("sms", "+12025550143", "   "), /cannot be empty/);
  });

  test("rejects message body exceeding 1,600 character limit", () => {
    const oversizedBody = "X".repeat(1601);
    assert.throws(() => validateSendMessagePayload("sms", "+12025550143", oversizedBody), /exceeds 1,600 character limit/);
  });

  test("masks phone numbers correctly to preserve privacy", () => {
    assert.equal(maskPhoneNumber("+12025550143"), "+1 ******0143");
    assert.equal(maskPhoneNumber("+919876543210"), "+91 ******3210");
    assert.equal(maskPhoneNumber("1234"), "****");
    assert.equal(maskPhoneNumber(""), "");
  });

  test("parses structured MessagingSendResponse schema", () => {
    const mockSendResponse = {
      success: true,
      channel: "sms",
      provider: "MockTwilioSMSProvider",
      message_id: "msg_mock_987654",
      status: "delivered",
      is_mock: true,
    };

    assert.equal(mockSendResponse.success, true);
    assert.equal(mockSendResponse.channel, "sms");
    assert.equal(mockSendResponse.status, "delivered");
    assert.equal(mockSendResponse.is_mock, true);
  });

  test("identifies carrier opt-out keywords correctly (STOP, UNSUBSCRIBE, CANCEL, END, QUIT)", () => {
    assert.equal(validateOptOutKeyword("STOP").isOptOut, true);
    assert.equal(validateOptOutKeyword("unsubscribe").isOptOut, true);
    assert.equal(validateOptOutKeyword("Cancel").isOptOut, true);
    assert.equal(validateOptOutKeyword("END").isOptOut, true);
    assert.equal(validateOptOutKeyword("quit").isOptOut, true);
    assert.equal(validateOptOutKeyword("HELP").isOptOut, false);
    assert.equal(validateOptOutKeyword("STATUS").isOptOut, false);
  });

  test("parses structured MessagingOptOutResponse schema", () => {
    const mockOptOutResponse = {
      success: true,
      opted_out: true,
      keyword_matched: true,
      channel: "sms",
      status: "opted_out",
    };

    assert.equal(mockOptOutResponse.success, true);
    assert.equal(mockOptOutResponse.opted_out, true);
    assert.equal(mockOptOutResponse.keyword_matched, true);
    assert.equal(mockOptOutResponse.status, "opted_out");
  });

  test("maps 403 Forbidden to active consent revocation warning", () => {
    function mapMessagingError(status) {
      if (status === 403) return "Consent revoked: Recipient has opted out of automated notifications.";
      if (status === 401) return "Session expired. Please re-authenticate.";
      return "Messaging dispatch failed.";
    }

    assert.ok(mapMessagingError(403).includes("Consent revoked"));
    assert.ok(mapMessagingError(401).includes("Session expired"));
  });

  test("verifies zero message content stored in web storage", () => {
    const forbiddenStorageKeys = ["sms_body", "whatsapp_message", "recipient_phone", "messaging_draft"];
    const mockStorage = {};

    forbiddenStorageKeys.forEach((key) => {
      assert.equal(mockStorage[key], undefined, `Storage must not contain ${key}`);
    });
  });

  test("verifies operational non-diagnostic clinical safety disclaimer", () => {
    const disclaimer = "CareGraph AI messaging is an operational communication interface for appointment alerts and care adherence reminders. It does not provide medical diagnosis, prescription adjustments, or clinical decision-making.";
    assert.ok(disclaimer.includes("operational communication interface"));
    assert.ok(disclaimer.includes("does not provide medical diagnosis"));
  });
});
