"""
tests/test_analytics.py

Automated test suite for Phase 11A Power BI & Analytics Integration:
- Authentication and RBAC enforcement (401 unauthenticated, 403 patient role)
- Server-side clinical operations aggregation
- Multi-agent telemetry aggregation
- Token cost intelligence and pricing accounting
- Zero-PHI compliance across all endpoints and export formats
- Tabular JSON and CSV export capabilities
"""

import pytest
import csv
import io
from fastapi.testclient import TestClient
from app.main import app
from app.services.telemetry import global_telemetry, global_cost_tracker
from app.database import SessionLocal
from app import crud, models

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def ensure_seed_and_telemetry_data():
    """Ensure database has seed data and telemetry collector has sample traces for tests."""
    db = SessionLocal()
    try:
        crud.seed_initial_data(db)
        patient_user = db.query(models.User).filter(models.User.username == "patient_demo").first()
        if patient_user and patient_user.patient:
            if db.query(models.Appointment).filter(models.Appointment.patient_id == patient_user.patient.id).count() == 0:
                appt = models.Appointment(
                    patient_id=patient_user.patient.id,
                    doctor_name="Dr. Sarah Jenkins",
                    specialty="Cardiology",
                    appointment_time="2026-09-10 10:00 AM",
                    status="scheduled",
                    notes="Follow-up consultation"
                )
                db.add(appt)
                db.commit()
    finally:
        db.close()

    # Record sample telemetry traces and cost usage if empty
    global_telemetry.record_workflow_event(
        session_id="analytics_test_session_1",
        user_id=1,
        intent="triage",
        selected_agent="triage_agent",
        latency_ms=120.5,
        status="SUCCESS",
        safety_escalated=False,
        token_usage={"prompt_tokens": 150, "completion_tokens": 50, "total_tokens": 200},
        tool_name="vector_search",
        actor_role="patient",
    )
    global_telemetry.record_workflow_event(
        session_id="analytics_test_session_2",
        user_id=1,
        intent="emergency",
        selected_agent="emergency_triage_agent",
        latency_ms=45.0,
        status="SAFETY_ESCALATED",
        safety_escalated=True,
        token_usage={"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
        tool_name=None,
        actor_role="patient",
    )

    global_cost_tracker.record_usage(
        model="llama-3.3-70b-versatile",
        prompt_tokens=500,
        completion_tokens=150,
        workflow_name="clinical_triage",
        session_id="analytics_test_session_1",
    )
    global_cost_tracker.record_usage(
        model="llama-3.1-8b-instant",
        prompt_tokens=200,
        completion_tokens=50,
        workflow_name="intent_routing",
        session_id="analytics_test_session_2",
    )


def get_admin_token_header():
    res = client.post("/auth/login", data={"username": "admin_demo", "password": "admin_pass"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_patient_token_header():
    res = client.post("/auth/login", data={"username": "patient_demo", "password": "patient_pass"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_analytics_endpoints_return_401():
    """Verify that all analytics endpoints reject unauthenticated requests with HTTP 401."""
    endpoints = [
        "/analytics/clinical-operations",
        "/analytics/agent-telemetry",
        "/analytics/cost-intelligence",
        "/analytics/export/appointments",
        "/analytics/export/medications",
        "/analytics/export/vitals",
        "/analytics/export/consents",
        "/analytics/export/agent-telemetry",
        "/analytics/export/cost-intelligence",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 401, f"{ep} did not return 401 for unauthenticated request"


def test_patient_role_analytics_endpoints_return_403():
    """Verify that users with role 'patient' receive HTTP 403 Forbidden for analytics routes."""
    patient_headers = get_patient_token_header()
    endpoints = [
        "/analytics/clinical-operations",
        "/analytics/agent-telemetry",
        "/analytics/cost-intelligence",
        "/analytics/export/appointments",
        "/analytics/export/medications",
        "/analytics/export/vitals",
        "/analytics/export/consents",
        "/analytics/export/agent-telemetry",
        "/analytics/export/cost-intelligence",
    ]
    for ep in endpoints:
        res = client.get(ep, headers=patient_headers)
        assert res.status_code == 403, f"{ep} did not return 403 for patient role"


def test_admin_clinical_operations_analytics_aggregation():
    """Verify server-side aggregation correctness for clinical operations analytics."""
    admin_headers = get_admin_token_header()
    res = client.get("/analytics/clinical-operations", headers=admin_headers)
    assert res.status_code == 200

    data = res.json()
    assert data["zero_phi"] is True
    assert data["total_patients"] >= 1

    appts = data["appointments"]
    assert appts["total_count"] >= 1
    assert "scheduled" in appts["by_status"] or len(appts["by_status"]) >= 1
    assert isinstance(appts["by_specialty"], dict)
    assert isinstance(appts["by_doctor"], dict)

    meds = data["medications"]
    assert meds["total_count"] >= 1
    assert meds["active_count"] >= 1
    assert isinstance(meds["by_name"], dict)

    vits = data["vitals"]
    assert vits["total_count"] >= 1
    assert isinstance(vits["by_type"], dict)

    cons = data["consents"]
    assert cons["total_count"] >= 1
    assert isinstance(cons["by_type"], dict)


def test_admin_agent_telemetry_analytics_aggregation():
    """Verify operational telemetry aggregation correctness for agent monitoring."""
    admin_headers = get_admin_token_header()
    res = client.get("/analytics/agent-telemetry", headers=admin_headers)
    assert res.status_code == 200

    data = res.json()
    assert data["zero_phi"] is True
    assert data["total_events"] >= 2
    assert data["avg_latency_ms"] >= 0.0
    assert data["safety_escalations"] >= 1
    assert "triage" in data["intents_breakdown"] or "emergency" in data["intents_breakdown"]
    assert isinstance(data["status_breakdown"], dict)
    assert isinstance(data["tool_breakdown"], dict)


def test_admin_cost_intelligence_analytics_aggregation():
    """Verify token cost accounting and model pricing intelligence aggregation."""
    admin_headers = get_admin_token_header()
    res = client.get("/analytics/cost-intelligence", headers=admin_headers)
    assert res.status_code == 200

    data = res.json()
    assert data["zero_phi"] is True
    assert data["total_prompt_tokens"] > 0
    assert data["total_completion_tokens"] > 0
    assert data["total_tokens"] > 0
    assert data["total_cost_usd"] > 0.0
    assert "llama-3.3-70b-versatile" in data["model_usage"]
    assert "llama-3.1-8b-instant" in data["model_usage"]
    assert "strong_tier" in data["tier_distribution"] or "fast_tier" in data["tier_distribution"]


def test_analytics_export_endpoints_json_and_csv():
    """Verify tabular JSON and CSV exports for all supported datasets."""
    admin_headers = get_admin_token_header()
    datasets = [
        "clinical-operations",
        "appointments",
        "medications",
        "vitals",
        "consents",
        "agent-telemetry",
        "cost-intelligence",
    ]

    for ds in datasets:
        # 1. Test JSON format
        res_json = client.get(f"/analytics/export/{ds}?format=json", headers=admin_headers)
        assert res_json.status_code == 200, f"Export JSON failed for {ds}"
        records = res_json.json()
        assert isinstance(records, list), f"Expected JSON list for {ds}"
        assert len(records) > 0, f"Expected non-empty records for {ds}"

        # 2. Test CSV format
        res_csv = client.get(f"/analytics/export/{ds}?format=csv", headers=admin_headers)
        assert res_csv.status_code == 200, f"Export CSV failed for {ds}"
        assert "text/csv" in res_csv.headers["content-type"]
        assert f"attachment; filename={ds}.csv" in res_csv.headers["content-disposition"]

        # Verify CSV parseability
        reader = csv.reader(io.StringIO(res_csv.text))
        rows = list(reader)
        assert len(rows) >= 2, f"CSV should contain header and at least one data row for {ds}"


def test_analytics_zero_phi_strict_compliance():
    """
    Verify that sensitive patient identifiers (names, emails, phones, notes, DOB, user IDs)
    are strictly excised from all analytics outputs.
    """
    admin_headers = get_admin_token_header()

    # Check clinical operations summary
    res = client.get("/analytics/clinical-operations", headers=admin_headers)
    text = res.text.lower()
    for forbidden in ["john", "doe", "john.doe@example.com", "+1-555-0199", "user_id", "password", "patient_id"]:
        assert forbidden not in text, f"Forbidden identifier '{forbidden}' found in clinical operations summary"

    # Check tabular exports
    for ds in ["appointments", "medications", "vitals", "consents"]:
        res_exp = client.get(f"/analytics/export/{ds}?format=json", headers=admin_headers)
        records = res_exp.json()
        for r in records:
            assert "patient_id" not in r, f"'patient_id' found in export {ds}"
            assert "user_id" not in r, f"'user_id' found in export {ds}"
            assert "notes" not in r, f"'notes' found in export {ds}"
            assert "email" not in r, f"'email' found in export {ds}"
            assert "phone" not in r, f"'phone' found in export {ds}"


def test_analytics_export_invalid_dataset_and_format_errors():
    """Verify error handling for invalid dataset names (404) and invalid format parameter (400)."""
    admin_headers = get_admin_token_header()

    # Invalid dataset -> 404
    res_404 = client.get("/analytics/export/unknown-dataset-123", headers=admin_headers)
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()

    # Invalid format -> 400
    res_400 = client.get("/analytics/export/appointments?format=xml", headers=admin_headers)
    assert res_400.status_code == 400
    assert "unsupported format" in res_400.json()["detail"].lower()
