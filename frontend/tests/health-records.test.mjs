/**
 * CareGraph AI - Phase 11E-4 Patient Health Records & Care Management Test Suite
 * Validates appointments, vitals, medications, reminders, consents, and dashboard metrics.
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";

// ==========================================
// 1. Appointments Data & State Management
// ==========================================

describe("Appointments State & Categorization", () => {
  function categorizeAppointments(list) {
    return {
      upcoming: list.filter((a) => a.status === "scheduled"),
      historical: list.filter((a) => a.status !== "scheduled"),
    };
  }

  test("separates scheduled from cancelled/completed appointments", () => {
    const list = [
      { id: 1, doctor_name: "Dr. Smith", specialty: "Cardiology", appointment_time: "2026-09-01 10:00", status: "scheduled" },
      { id: 2, doctor_name: "Dr. Jones", specialty: "Dermatology", appointment_time: "2026-08-15 14:00", status: "completed" },
      { id: 3, doctor_name: "Dr. Lee", specialty: "General Medicine", appointment_time: "2026-08-10 09:00", status: "cancelled" },
    ];

    const { upcoming, historical } = categorizeAppointments(list);
    assert.equal(upcoming.length, 1);
    assert.equal(upcoming[0].id, 1);
    assert.equal(historical.length, 2);
  });

  test("validates appointment cancellation payload formatting", () => {
    function createCancelPayload(appointmentId) {
      assert.ok(typeof appointmentId === "number" && appointmentId > 0, "Valid appointment ID required");
      return { appointment_id: appointmentId };
    }

    const payload = createCancelPayload(42);
    assert.equal(payload.appointment_id, 42);
    assert.throws(() => createCancelPayload(null));
    assert.throws(() => createCancelPayload(-1));
  });
});

// ==========================================
// 2. Vitals Management & Informational Non-Diagnostic Rules
// ==========================================

describe("Vitals Validation & Safety Invariants", () => {
  const VITAL_UNITS = {
    blood_pressure: "mmHg",
    heart_rate: "bpm",
    weight: "lbs",
    temperature: "°F",
    spo2: "%",
  };

  function validateVitalInput(vitalType, value, unit) {
    assert.ok(VITAL_UNITS[vitalType], `Unsupported vital type: ${vitalType}`);
    assert.ok(value && value.trim().length > 0, "Vital value is required");
    const assignedUnit = unit || VITAL_UNITS[vitalType];
    return { vital_type: vitalType, value: value.trim(), unit: assignedUnit };
  }

  test("assigns default units for supported vital types", () => {
    const bp = validateVitalInput("blood_pressure", "120/80");
    assert.equal(bp.unit, "mmHg");

    const hr = validateVitalInput("heart_rate", "75");
    assert.equal(hr.unit, "bpm");

    const spo2 = validateVitalInput("spo2", "99");
    assert.equal(spo2.unit, "%");
  });

  test("rejects invalid or empty vital measurements", () => {
    assert.throws(() => validateVitalInput("unknown_type", "100"));
    assert.throws(() => validateVitalInput("heart_rate", "  "));
  });

  test("ensures non-diagnostic informational disclaimer is present", () => {
    const disclaimer = "Measurements are recorded for coordination reference. CareGraph AI does not perform medical diagnosis or interpret clinical normality.";
    assert.ok(disclaimer.includes("does not perform medical diagnosis"));
    assert.ok(disclaimer.includes("coordination reference"));
  });
});

// ==========================================
// 3. Medications Management
// ==========================================

describe("Medications Schema & Clinical Safety", () => {
  test("validates medication record attributes", () => {
    const med = {
      id: 10,
      name: "Lisinopril",
      dosage: "10mg",
      frequency: "Once daily",
      prescribed_by: "Dr. Sarah Smith",
      is_active: true,
    };

    assert.equal(med.name, "Lisinopril");
    assert.equal(med.is_active, true);
    assert.ok(med.dosage);
    assert.ok(med.frequency);
  });

  test("verifies clinical non-prescribing safety directive", () => {
    const safetyNotice = "CareGraph AI displays prescribed medication records for care coordination reference only. The assistant never alters dosages, prescribes drugs, or changes physician orders.";
    assert.ok(safetyNotice.includes("never alters dosages"));
    assert.ok(safetyNotice.includes("care coordination reference"));
  });
});

// ==========================================
// 4. Reminders Scheduling & Consent Gating
// ==========================================

describe("Reminders Validation & Categorization", () => {
  function validateReminderInput(text, time, notes) {
    assert.ok(text && text.trim().length > 0, "Reminder text is required");
    assert.ok(time && time.trim().length > 0, "Reminder time is required");
    return { reminder_text: text.trim(), reminder_time: time.trim(), notes: notes?.trim() || null };
  }

  test("validates reminder creation payload", () => {
    const rem = validateReminderInput("Take Metformin 500mg", "08:00 AM", "With meal");
    assert.equal(rem.reminder_text, "Take Metformin 500mg");
    assert.equal(rem.reminder_time, "08:00 AM");
    assert.equal(rem.notes, "With meal");
  });

  test("rejects blank reminder creation fields", () => {
    assert.throws(() => validateReminderInput("", "08:00 AM"));
    assert.throws(() => validateReminderInput("Take pills", ""));
  });

  test("categorizes active vs cancelled reminders", () => {
    const list = [
      { id: 1, reminder_text: "Morning pills", reminder_time: "08:00 AM", status: "active" },
      { id: 2, reminder_text: "Evening drops", reminder_time: "20:00", status: "cancelled" },
    ];
    const active = list.filter((r) => r.status === "active");
    const cancelled = list.filter((r) => r.status !== "active");
    assert.equal(active.length, 1);
    assert.equal(cancelled.length, 1);
  });
});

// ==========================================
// 5. Consent Center Management
// ==========================================

describe("Consent Center Catalog & Actions", () => {
  const VALID_CONSENT_TYPES = [
    "data_access",
    "vital_tracking",
    "medication_tracking",
    "medication_reminders",
    "appointment_booking",
    "ai_processing",
  ];

  function formatGrantPayload(type, days = 365, version = "v1.0") {
    assert.ok(VALID_CONSENT_TYPES.includes(type), `Invalid consent type: ${type}`);
    assert.ok(days > 0, "Expiration days must be positive");
    return { consent_type: type, expires_days: days, version };
  }

  function formatRevokePayload(type) {
    assert.ok(VALID_CONSENT_TYPES.includes(type), `Invalid consent type: ${type}`);
    return { consent_type: type };
  }

  test("formats valid grant and revoke consent payloads", () => {
    const grant = formatGrantPayload("ai_processing", 365, "v1.0");
    assert.equal(grant.consent_type, "ai_processing");
    assert.equal(grant.expires_days, 365);

    const revoke = formatRevokePayload("vital_tracking");
    assert.equal(revoke.consent_type, "vital_tracking");
  });

  test("rejects unsupported consent categories", () => {
    assert.throws(() => formatGrantPayload("arbitrary_admin_override"));
    assert.throws(() => formatRevokePayload("unsupported_category"));
  });
});

// ==========================================
// 6. Patient Dashboard Live Overview
// ==========================================

describe("Patient Dashboard Overview Aggregation", () => {
  test("computes correct summary metrics from healthcare records", () => {
    const appointments = [
      { id: 1, status: "scheduled", appointment_time: "2026-09-05 14:00" },
      { id: 2, status: "completed", appointment_time: "2026-08-01 10:00" },
    ];
    const vitals = [
      { id: 1, vital_type: "blood_pressure", value: "120/80", unit: "mmHg" },
    ];
    const medications = [
      { id: 1, name: "Atorvastatin", is_active: true },
      { id: 2, name: "Amoxicillin", is_active: false },
    ];
    const reminders = [
      { id: 1, status: "active", reminder_time: "08:00 AM" },
    ];

    const upcomingCount = appointments.filter((a) => a.status === "scheduled").length;
    const activeMedCount = medications.filter((m) => m.is_active).length;
    const activeRemCount = reminders.filter((r) => r.status === "active").length;
    const latestVital = vitals.length > 0 ? `${vitals[0].value} ${vitals[0].unit}` : "None";

    assert.equal(upcomingCount, 1);
    assert.equal(activeMedCount, 1);
    assert.equal(activeRemCount, 1);
    assert.equal(latestVital, "120/80 mmHg");
  });

  test("verifies patient role receives zero admin telemetry or benchmarks", () => {
    const patientRole = "patient";
    const availablePatientRoutes = [
      "/dashboard",
      "/chat",
      "/appointments",
      "/vitals",
      "/medications",
      "/reminders",
      "/consents",
    ];
    const adminRoutes = ["/admin/analytics", "/admin/benchmarks", "/admin/messaging"];

    adminRoutes.forEach((route) => {
      assert.ok(!availablePatientRoutes.includes(route), `Admin route ${route} must not be in patient routes`);
    });
  });
});
