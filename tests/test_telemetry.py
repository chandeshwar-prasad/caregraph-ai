"""
tests/test_telemetry.py

Tests for Phase 9 Milestone 1:
Telemetry & Tracing Architecture, Zero-PHI Redaction Engine,
Span Attributes, Latency Tracking, and Non-blocking Collector.
"""

import time
import pytest
from fastapi.testclient import TestClient
from app.services.telemetry import (
    redact_phi,
    TelemetrySpan,
    TelemetryCollector,
    trace_span,
    global_telemetry,
)
from app.services.graph import graph
from app.main import app

client = TestClient(app)


def test_phi_redaction_strings_emails_phones():
    """Verify that email addresses and phone numbers are scrubbed from telemetry strings."""
    raw_text = "Contact patient at john.doe@hospital.org or +1-555-839-2001 regarding prescription."
    sanitized = redact_phi(raw_text)
    assert "john.doe@hospital.org" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized
    assert "555-839-2001" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized


def test_phi_redaction_nested_dictionaries():
    """Verify that sensitive keys (passwords, notes, prompts, SSN) in nested dicts are masked."""
    payload = {
        "user_id": 101,
        "actor_role": "patient",
        "password": "super_secret_password_123",
        "user_message": "I have been experiencing severe dizzy spells and nausea for two weeks",
        "notes": "Patient reports family history of cardiovascular issues",
        "metadata": {
            "session_id": "sess_1234",
            "secret_key": "jwt_secret_token_val",
            "safe_counter": 5
        }
    }
    sanitized = redact_phi(payload)

    assert sanitized["user_id"] == 101
    assert sanitized["actor_role"] == "patient"
    assert sanitized["password"] == f"[REDACTED_TEXT: len={len(payload['password'])}]"
    assert sanitized["user_message"] == f"[REDACTED_TEXT: len={len(payload['user_message'])}]"
    assert sanitized["notes"] == f"[REDACTED_TEXT: len={len(payload['notes'])}]"
    assert sanitized["metadata"]["safe_counter"] == 5
    assert sanitized["metadata"]["secret_key"] == f"[REDACTED_TEXT: len={len(payload['metadata']['secret_key'])}]"


def test_telemetry_span_lifecycle_and_duration():
    """Verify that TelemetrySpan records accurate duration and status."""
    span = TelemetrySpan(name="test_tool_execution", span_type="tool", attributes={"tool_name": "get_patient_vitals"})
    time.sleep(0.02)  # sleep 20ms
    span.finish(status="SUCCESS", extra_attributes={"records_count": 3})

    data = span.to_dict()
    assert data["name"] == "test_tool_execution"
    assert data["span_type"] == "tool"
    assert data["status"] == "SUCCESS"
    assert data["duration_ms"] >= 15.0  # Measured duration in ms
    assert data["attributes"]["tool_name"] == "get_patient_vitals"
    assert data["attributes"]["records_count"] == 3


def test_trace_span_context_manager():
    """Verify that trace_span context manager auto-records to collector and handles errors gracefully."""
    collector = TelemetryCollector()
    
    # Successful span
    with trace_span("database_lookup", span_type="db", attributes={"table": "patients"}):
        time.sleep(0.01)
    
    # Error span
    with pytest.raises(ValueError):
        with trace_span("failing_operation", span_type="agent"):
            raise ValueError("Simulated network timeout")

    # Global telemetry collector must have recorded spans
    assert len(global_telemetry.traces) >= 2


def test_telemetry_collector_metrics_summary():
    """Verify that TelemetryCollector computes accurate aggregate summaries."""
    collector = TelemetryCollector()
    collector.clear()

    collector.record_workflow_event("sess_1", 1, "triage", "triage", 45.0, "SUCCESS")
    collector.record_workflow_event("sess_2", 2, "scheduling", "scheduling", 80.0, "SUCCESS")
    collector.record_workflow_event("sess_3", 3, "emergency", "emergency_safety", 5.0, "SAFETY_ESCALATED", safety_escalated=True)
    collector.record_workflow_event("sess_4", 4, "records", "records", 30.0, "ERROR")

    summary = collector.get_summary()
    assert summary["total_events"] == 4
    assert summary["safety_escalations"] == 1
    assert summary["error_rate"] == 0.25
    assert summary["avg_latency_ms"] == 40.0
    assert summary["intents_breakdown"]["triage"] == 1
    assert summary["intents_breakdown"]["scheduling"] == 1
    assert summary["intents_breakdown"]["emergency"] == 1


def test_zero_phi_in_workflow_telemetry_records():
    """Verify that workflow telemetry events never contain raw clinical notes or user passwords."""
    collector = TelemetryCollector()
    collector.clear()

    event = collector.record_workflow_event(
        session_id="session_phi_check_100",
        user_id=88,
        intent="records",
        selected_agent="patient_data",
        latency_ms=12.5,
        status="SUCCESS",
        tool_name="get_patient_medications"
    )

    assert event["user_id"] == 88
    assert event["intent"] == "records"
    assert event["tool_name"] == "get_patient_medications"
    assert "user_message" not in event
    assert "password" not in event
    assert "notes" not in event


def test_graph_execution_records_telemetry():
    """Verify that multi-agent graph execution automatically produces a sanitized telemetry event."""
    global_telemetry.clear()

    config = {"configurable": {"thread_id": "test_graph_telemetry_sess"}}
    state = graph.invoke(
        {
            "user_message": "What is the guidance for mild fever?",
            "user_id": 1,
            "user_role": "patient",
            "session_id": "test_graph_telemetry_sess"
        },
        config=config
    )

    assert len(global_telemetry.traces) >= 1
    recent = global_telemetry.traces[-1]
    assert recent["session_id"] == "test_graph_telemetry_sess"
    assert recent["intent"] in ["triage", "general"]
    assert "user_message" not in recent


def test_emergency_safety_precedence_in_telemetry():
    """Verify that red-flag emergency queries record SAFETY_ESCALATED in telemetry."""
    global_telemetry.clear()

    config = {"configurable": {"thread_id": "test_emergency_telemetry"}}
    state = graph.invoke(
        {
            "user_message": "Severe crushing chest pain and shortness of breath",
            "user_id": 1,
            "user_role": "patient",
            "session_id": "test_emergency_telemetry"
        },
        config=config
    )

    assert state["safety_escalated"] is True
    assert len(global_telemetry.traces) >= 1
    recent = global_telemetry.traces[-1]
    assert recent["status"] == "SAFETY_ESCALATED"
    assert recent["safety_escalated"] is True


def test_telemetry_api_endpoint():
    """Verify FastAPI /metrics/telemetry endpoint returns sanitized summary metrics."""
    res = client.get("/metrics/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert "total_events" in data
    assert "avg_latency_ms" in data
    assert "safety_escalations" in data
    assert "error_rate" in data
    assert "intents_breakdown" in data
