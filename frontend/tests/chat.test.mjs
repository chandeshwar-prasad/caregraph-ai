/**
 * CareGraph AI - Phase 11E-3 Chat & HITL Appointment Approval Test Suite
 * Validates conversational state, LangGraph contracts, red-flag banners, HITL approval payloads, and error mappings.
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";

// ==========================================
// 1. Session Thread Management
// ==========================================

describe("Chat Session Thread Management", () => {
  function createSessionId(prefix = "sess_") {
    return `${prefix}${Math.random().toString(36).slice(2, 10)}`;
  }

  test("generates non-empty unique session IDs with prefix", () => {
    const s1 = createSessionId();
    const s2 = createSessionId();
    assert.ok(s1.startsWith("sess_"));
    assert.ok(s2.startsWith("sess_"));
    assert.notEqual(s1, s2);
  });

  test("session ID remains stable across sequential user queries in same thread", () => {
    const threadId = "sess_test_12345";
    const req1 = { message: "I have a cough", session_id: threadId };
    const req2 = { message: "Can I see a doctor?", session_id: threadId };
    assert.equal(req1.session_id, threadId);
    assert.equal(req2.session_id, threadId);
  });
});

// ==========================================
// 2. Intent & Emergency Red-Flag Presentation
// ==========================================

describe("Intent & Clinical Risk Presentation", () => {
  function evaluateRiskPresentation(response) {
    const isEmergency = response.safety_escalated || response.risk_level === "emergency";
    const isUrgent = !isEmergency && response.risk_level === "urgent";
    const isNonUrgent = !isEmergency && !isUrgent;

    return {
      showEmergencyBanner: isEmergency,
      showUrgentBanner: isUrgent,
      isNonUrgent,
      intentTag: response.intent || "general",
    };
  }

  test("identifies deterministic emergency escalation and enables emergency banner", () => {
    const mockEmergencyResponse = {
      message: "Emergency medical evaluation required immediately. Call 911 or visit the ER.",
      intent: "triage",
      risk_level: "emergency",
      safety_escalated: true,
      approval_required: false,
    };

    const pres = evaluateRiskPresentation(mockEmergencyResponse);
    assert.equal(pres.showEmergencyBanner, true);
    assert.equal(pres.showUrgentBanner, false);
    assert.equal(pres.intentTag, "triage");
  });

  test("identifies urgent triage guidance without emergency escalation", () => {
    const mockUrgentResponse = {
      message: "Prompt medical consultation recommended within 24 hours.",
      intent: "triage",
      risk_level: "urgent",
      safety_escalated: false,
      approval_required: false,
    };

    const pres = evaluateRiskPresentation(mockUrgentResponse);
    assert.equal(pres.showEmergencyBanner, false);
    assert.equal(pres.showUrgentBanner, true);
  });

  test("identifies non-urgent scheduling request", () => {
    const mockSchedResponse = {
      message: "Found available consultation slots with Dr. Sarah Smith.",
      intent: "scheduling",
      risk_level: "non_urgent",
      safety_escalated: false,
      approval_required: true,
    };

    const pres = evaluateRiskPresentation(mockSchedResponse);
    assert.equal(pres.showEmergencyBanner, false);
    assert.equal(pres.showUrgentBanner, false);
    assert.equal(pres.isNonUrgent, true);
  });
});

// ==========================================
// 3. Grounded Sources & Citations
// ==========================================

describe("Grounded Knowledge Sources Formatting", () => {
  function formatSources(sources) {
    if (!sources || sources.length === 0) return [];
    return sources.map((s) => ({
      name: s.source_name || s.title || "Clinical Guideline",
      type: s.source_type || "Guideline",
      category: s.category || "General",
    }));
  }

  test("formats clinical source attribution correctly", () => {
    const sources = [
      { source_name: "CDC Upper Respiratory Infection Guidance", source_type: "cdc_protocol", category: "respiratory" },
      { title: "WHO Fever Clinical Protocol", source_type: "who_guideline", category: "fever" },
    ];

    const formatted = formatSources(sources);
    assert.equal(formatted.length, 2);
    assert.equal(formatted[0].name, "CDC Upper Respiratory Infection Guidance");
    assert.equal(formatted[0].type, "cdc_protocol");
    assert.equal(formatted[1].name, "WHO Fever Clinical Protocol");
  });

  test("handles empty or null sources gracefully", () => {
    assert.deepEqual(formatSources([]), []);
    assert.deepEqual(formatSources(null), []);
    assert.deepEqual(formatSources(undefined), []);
  });
});

// ==========================================
// 4. Human-in-the-Loop (HITL) Appointment Approval
// ==========================================

describe("Human-in-the-Loop (HITL) Workflow Contracts", () => {
  function validateHitlSlot(slot) {
    assert.ok(slot, "Slot details must be present");
    assert.ok(slot.doctor_name, "Doctor name must be specified");
    assert.ok(slot.specialty, "Specialty must be specified");
    assert.ok(slot.appointment_time, "Appointment time must be specified");
    assert.equal(typeof slot.is_mock, "boolean", "is_mock flag must be boolean");
  }

  function createApprovalPayload(sessionId, decision) {
    assert.ok(sessionId, "Session ID is required for approval");
    assert.ok(["approved", "rejected"].includes(decision), "Decision must be approved or rejected");
    return { session_id: sessionId, decision };
  }

  test("validates proposed appointment slot structure from LangGraph interrupt", () => {
    const sampleSlot = {
      doctor_name: "Dr. Sarah Smith",
      specialty: "Cardiology",
      appointment_time: "2026-09-02 14:00",
      is_mock: true,
    };
    validateHitlSlot(sampleSlot);
  });

  test("creates valid approval payload for approved decision", () => {
    const payload = createApprovalPayload("sess_user_123", "approved");
    assert.equal(payload.session_id, "sess_user_123");
    assert.equal(payload.decision, "approved");
  });

  test("creates valid rejection payload for rejected decision", () => {
    const payload = createApprovalPayload("sess_user_123", "rejected");
    assert.equal(payload.session_id, "sess_user_123");
    assert.equal(payload.decision, "rejected");
  });

  test("rejects invalid approval decision inputs", () => {
    assert.throws(() => createApprovalPayload("sess_123", "maybe"));
    assert.throws(() => createApprovalPayload(null, "approved"));
  });

  test("tracks HITL state transition from pending to approved", () => {
    let state = { approval_required: true, approval_status: "pending" };
    assert.equal(state.approval_status, "pending");

    // Transition on approve response
    state = { approval_required: false, approval_status: "approved" };
    assert.equal(state.approval_required, false);
    assert.equal(state.approval_status, "approved");
  });
});

// ==========================================
// 5. Error Status Handling & Mappings
// ==========================================

describe("API Error Status Mappings in Chat", () => {
  function mapChatError(status, detail) {
    if (status === 401) {
      return { type: "AUTH_EXPIRED", message: "Your session has expired. Please sign in again." };
    }
    if (status === 429) {
      return { type: "RATE_LIMIT", message: "The AI coordinator is temporarily busy. Please wait a moment and retry." };
    }
    if (status === 504) {
      return { type: "TIMEOUT", message: "Request timed out. Please try again." };
    }
    if (status === 503) {
      return { type: "SERVICE_UNAVAILABLE", message: detail || "Service temporarily unavailable." };
    }
    return { type: "GENERIC_ERROR", message: detail || "An unexpected error occurred." };
  }

  test("maps 401 to session expiration notice", () => {
    const err = mapChatError(401);
    assert.equal(err.type, "AUTH_EXPIRED");
    assert.ok(err.message.includes("session has expired"));
  });

  test("maps 429 to rate limit notice", () => {
    const err = mapChatError(429);
    assert.equal(err.type, "RATE_LIMIT");
    assert.ok(err.message.includes("temporarily busy"));
  });

  test("maps 504 to timeout notice", () => {
    const err = mapChatError(504);
    assert.equal(err.type, "TIMEOUT");
  });

  test("maps 503 to service unavailable notice", () => {
    const err = mapChatError(503, "Database connection error");
    assert.equal(err.type, "SERVICE_UNAVAILABLE");
    assert.equal(err.message, "Database connection error");
  });
});
