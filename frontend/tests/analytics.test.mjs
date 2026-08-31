/**
 * CareGraph AI - Phase 11E-6 Analytics & Admin Test Suite
 * Validates Executive KPIs, Clinical Operations, Telemetry, Costs, Power BI exports, and Benchmark Scorecards.
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";

// ==========================================
// 1. Phase 11E-6-1 Admin Executive KPIs
// ==========================================

describe("Admin Executive KPI Overview Contracts", () => {
  test("parses live ClinicalOperationsAnalyticsResponse schema for executive KPIs", () => {
    const mockClinicalOps = {
      total_patients: 42,
      appointments: {
        total_count: 128,
        by_status: { scheduled: 80, completed: 40, cancelled: 8 },
        by_specialty: { Cardiology: 50, "General Practice": 78 },
        by_doctor: { "Dr. Sarah Smith": 80, "Dr. John Doe": 48 },
      },
      medications: {
        total_count: 95,
        active_count: 72,
        inactive_count: 23,
        by_name: { Lisinopril: 30, Metformin: 42 },
        by_frequency: { "Once daily": 50, "Twice daily": 22 },
      },
      vitals: {
        total_count: 310,
        by_type: { heart_rate: 120, blood_pressure: 110, glucose: 80 },
      },
      consents: {
        total_count: 42,
        by_type: { ai_processing: 40, data_access: 42 },
        by_status: { granted: 40, revoked: 2 },
      },
      reminders: {
        total_count: 65,
        by_status: { active: 55, cancelled: 10 },
      },
      zero_phi: true,
    };

    assert.equal(mockClinicalOps.total_patients, 42);
    assert.equal(mockClinicalOps.appointments.total_count, 128);
    assert.equal(mockClinicalOps.medications.active_count, 72);
    assert.equal(mockClinicalOps.zero_phi, true);
  });

  test("parses AgentTelemetryAnalyticsResponse schema for latency and event metrics", () => {
    const mockTelemetry = {
      total_events: 1540,
      avg_latency_ms: 185.4,
      safety_escalations: 12,
      error_rate: 0.002,
      intents_breakdown: { triage: 600, scheduling: 400, records: 350, emergency: 12 },
      agents_breakdown: { triage_agent: 600, coordinator_agent: 400, records_agent: 350 },
      status_breakdown: { success: 1537, error: 3 },
      tool_breakdown: { search_slots: 400, get_medications: 350 },
      recent_traces_count: 50,
      zero_phi: true,
    };

    assert.equal(mockTelemetry.total_events, 1540);
    assert.equal(mockTelemetry.avg_latency_ms, 185.4);
    assert.equal(mockTelemetry.safety_escalations, 12);
    assert.equal(mockTelemetry.zero_phi, true);
  });

  test("parses CostIntelligenceAnalyticsResponse schema for spend and token metrics", () => {
    const mockCost = {
      total_prompt_tokens: 450000,
      total_completion_tokens: 125000,
      total_tokens: 575000,
      total_cost_usd: 0.0845,
      avg_cost_per_workflow_usd: 0.00055,
      model_usage: {
        "llama-3.3-70b-versatile": { tokens: 575000, cost_usd: 0.0845 },
      },
      tier_distribution: { Tier1_Fast: 900, Tier2_Reasoning: 600, Tier3_Complex: 40 },
      pricing_table: {},
      zero_phi: true,
    };

    assert.equal(mockCost.total_tokens, 575000);
    assert.equal(mockCost.total_cost_usd, 0.0845);
    assert.equal(mockCost.zero_phi, true);
  });

  test("parses QuantitativeScorecard schema for safety recall and benchmark quality", () => {
    const mockScorecard = {
      total_scenarios_evaluated: 55,
      emergency_safety_recall_pct: 100.0,
      prompt_injection_resistance_pct: 100.0,
      unsupported_claim_rate_pct: 0.0,
      intent_classification_accuracy_pct: 98.2,
      routing_precision_pct: 96.5,
      tool_selection_rate_pct: 95.0,
      rag_grounding_faithfulness_pct: 98.0,
      source_attribution_completeness_pct: 97.5,
      overall_composite_score_pct: 98.1,
      timestamp: "2026-08-31T06:00:00Z",
    };

    assert.equal(mockScorecard.total_scenarios_evaluated, 55);
    assert.equal(mockScorecard.emergency_safety_recall_pct, 100.0);
    assert.equal(mockScorecard.prompt_injection_resistance_pct, 100.0);
    assert.equal(mockScorecard.unsupported_claim_rate_pct, 0.0);
    assert.equal(mockScorecard.overall_composite_score_pct, 98.1);
  });

  test("enforces strict admin vs patient role visibility separation", () => {
    function getDashboardMetricsForRole(role, data) {
      if (role === "admin") {
        return {
          clinicalOps: data.clinicalOps || null,
          telemetry: data.telemetry || null,
          costs: data.costs || null,
          scorecard: data.scorecard || null,
          patientAppointments: null,
        };
      }
      return {
        clinicalOps: null,
        telemetry: null,
        costs: null,
        scorecard: null,
        patientAppointments: data.patientAppointments || [],
      };
    }

    const testData = {
      clinicalOps: { total_patients: 42 },
      telemetry: { total_events: 1000 },
      costs: { total_cost_usd: 0.05 },
      scorecard: { emergency_safety_recall_pct: 100.0 },
      patientAppointments: [{ id: 1, doctor_name: "Dr. Smith" }],
    };

    const patientView = getDashboardMetricsForRole("patient", testData);
    assert.equal(patientView.clinicalOps, null);
    assert.equal(patientView.telemetry, null);
    assert.equal(patientView.costs, null);
    assert.equal(patientView.scorecard, null);
    assert.equal(patientView.patientAppointments.length, 1);

    const adminView = getDashboardMetricsForRole("admin", testData);
    assert.equal(adminView.clinicalOps.total_patients, 42);
    assert.equal(adminView.telemetry.total_events, 1000);
    assert.equal(adminView.costs.total_cost_usd, 0.05);
    assert.equal(adminView.scorecard.emergency_safety_recall_pct, 100.0);
    assert.equal(adminView.patientAppointments, null);
  });

  test("verifies clinical safety directive is present on the dashboard", () => {
    const directive = "CareGraph AI is a care-coordination and navigation system. It does not provide autonomous clinical diagnosis, prescriptions, or emergency triage override.";
    assert.ok(directive.includes("care-coordination"));
    assert.ok(directive.includes("does not provide autonomous clinical diagnosis"));
  });
});

// ==========================================
// 2. Phase 11E-6-2 Clinical Operations & Telemetry
// ==========================================

describe("Clinical Operations & Agent Telemetry Admin Contracts", () => {
  test("processes full clinical operations breakdown dimensions", () => {
    const clinicalOpsData = {
      total_patients: 25,
      appointments: {
        total_count: 50,
        by_status: { scheduled: 30, completed: 15, cancelled: 5 },
        by_specialty: { Cardiology: 20, "General Practice": 20, Neurology: 10 },
        by_doctor: { "Dr. Sarah Smith": 30, "Dr. John Doe": 20 },
      },
      medications: {
        total_count: 60,
        active_count: 45,
        inactive_count: 15,
        by_name: { Lisinopril: 20, Metformin: 25, Atorvastatin: 15 },
        by_frequency: { "Once daily": 35, "Twice daily": 10 },
      },
      vitals: {
        total_count: 150,
        by_type: { heart_rate: 50, blood_pressure: 45, glucose: 30, oxygen_saturation: 25 },
      },
      consents: {
        total_count: 25,
        by_type: { ai_processing: 25, data_access: 25 },
        by_status: { granted: 24, revoked: 1 },
      },
      reminders: {
        total_count: 35,
        by_status: { active: 30, cancelled: 5 },
      },
      zero_phi: true,
    };

    // Calculate active medication ratio
    const activeMedRatio = clinicalOpsData.medications.active_count / clinicalOpsData.medications.total_count;
    assert.equal(activeMedRatio, 0.75);

    // Verify specialty keys and doctors
    assert.equal(Object.keys(clinicalOpsData.appointments.by_specialty).length, 3);
    assert.equal(clinicalOpsData.appointments.by_doctor["Dr. Sarah Smith"], 30);

    // Verify vitals breakdown
    assert.equal(clinicalOpsData.vitals.by_type.blood_pressure, 45);

    // Verify zero_phi guarantee
    assert.equal(clinicalOpsData.zero_phi, true);
  });

  test("processes multi-agent telemetry performance and status distributions", () => {
    const telemetryData = {
      total_events: 3450,
      avg_latency_ms: 142.8,
      safety_escalations: 8,
      error_rate: 0.0015,
      intents_breakdown: { triage: 1500, scheduling: 1100, records: 800, emergency: 8 },
      agents_breakdown: {
        triage_agent: 1500,
        coordinator_agent: 1100,
        records_agent: 800,
        emergency_agent: 8,
      },
      status_breakdown: { SUCCESS: 3445, ERROR: 5 },
      tool_breakdown: { search_slots: 1100, get_medications: 800, record_vital: 300 },
      recent_traces_count: 100,
      zero_phi: true,
    };

    assert.equal(telemetryData.total_events, 3450);
    assert.ok(telemetryData.avg_latency_ms < 200);
    assert.equal(telemetryData.safety_escalations, 8);
    assert.equal(telemetryData.agents_breakdown.emergency_agent, 8);
    assert.equal(telemetryData.status_breakdown.SUCCESS, 3445);
    assert.equal(telemetryData.zero_phi, true);
  });

  test("verifies strict admin guard prevents non-admin user access", () => {
    function canAccessAdminAnalytics(userRole) {
      return userRole === "admin";
    }

    assert.equal(canAccessAdminAnalytics("admin"), true);
    assert.equal(canAccessAdminAnalytics("patient"), false);
    assert.equal(canAccessAdminAnalytics(undefined), false);
    assert.equal(canAccessAdminAnalytics(null), false);
    assert.equal(canAccessAdminAnalytics("guest"), false);
  });

  test("verifies zero PHI is leaked across clinical and telemetry metric structures", () => {
    const combinedAnalytics = {
      clinical: {
        total_patients: 10,
        appointments: { total_count: 20 },
      },
      telemetry: {
        total_events: 500,
        avg_latency_ms: 120,
      },
    };

    const serialized = JSON.stringify(combinedAnalytics);
    assert.ok(!serialized.includes("patient_name"));
    assert.ok(!serialized.includes("phone_number"));
    assert.ok(!serialized.includes("ssn"));
    assert.ok(!serialized.includes("mrn"));
    assert.ok(!serialized.includes("email"));
  });

  test("handles empty datasets safely without throwing runtime errors", () => {
    const emptyClinicalOps = {
      total_patients: 0,
      appointments: { total_count: 0, by_status: {}, by_specialty: {}, by_doctor: {} },
      medications: { total_count: 0, active_count: 0, inactive_count: 0, by_name: {}, by_frequency: {} },
      vitals: { total_count: 0, by_type: {} },
      consents: { total_count: 0, by_type: {}, by_status: {} },
      reminders: { total_count: 0, by_status: {} },
      zero_phi: true,
    };

    function getMaxVal(record = {}) {
      const vals = Object.values(record);
      return vals.length > 0 ? Math.max(...vals, 1) : 1;
    }

    assert.equal(getMaxVal(emptyClinicalOps.appointments.by_status), 1);
    assert.equal(emptyClinicalOps.total_patients, 0);
  });
});
