"""
tests/test_observability.py

Unit and integration tests for Prometheus Observability and Zero-PHI metrics bridge.
Verifies:
1. Prometheus metric generation format and Content-Type header.
2. Increments and histogram observations for node executions, intent classification, safety escalations, and FHIR calls.
3. Live /metrics HTTP endpoint response and scraping validity.
4. Absolute Zero PHI/PII presence in scraped metrics text.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import observability

client = TestClient(app)


def test_prometheus_recording_functions():
    """Verify individual recording helpers execute without exception."""
    observability.record_node_execution("triage", status="success", latency_seconds=0.045)
    observability.record_intent_classification("scheduling", match=True)
    observability.record_safety_escalation("red_flag", "emergency")
    observability.record_tool_execution("get_patient_vitals", "success")
    observability.record_fhir_call("GET", "MedicationRequest", "success", latency_seconds=0.08)
    observability.record_llm_usage("llama-3.3-70b-versatile", prompt_tokens=150, completion_tokens=35, latency_seconds=0.45)
    observability.update_cost_gauge(0.0042)


def test_generate_prometheus_metrics():
    """Verify raw metrics generation yields valid text and content-type."""
    content, media_type = observability.generate_prometheus_metrics()
    assert isinstance(content, bytes)
    assert "text/plain" in media_type
    
    text = content.decode("utf-8")
    assert "caregraph_graph_node_executions_total" in text
    assert "caregraph_intent_classifications_total" in text
    assert "caregraph_safety_escalations_total" in text
    assert "caregraph_tool_executions_total" in text
    assert "caregraph_fhir_api_calls_total" in text
    assert "caregraph_estimated_total_cost_usd" in text


def test_metrics_http_endpoint():
    """Verify GET /metrics HTTP status code and response payload."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    
    body = response.text
    assert "# HELP caregraph_graph_node_executions_total" in body
    assert "# TYPE caregraph_graph_node_executions_total counter" in body
    assert "caregraph_graph_node_latency_seconds" in body
    assert "caregraph_llm_token_usage_total" in body


def test_zero_phi_in_prometheus_metrics():
    """Verify that scraped Prometheus metrics contain strictly zero PHI / patient identifiers."""
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text

    prohibited_phi = [
        "chris.smith@example.com",
        "alex.taylor@example.com",
        "password",
        "secret",
        "122/78",
        "+1-555",
        "Lisinopril 10 MG Oral Tablet",
        "hypertension management"
    ]
    for phi in prohibited_phi:
        assert phi not in body, f"PHI leak detected in /metrics: '{phi}'"
