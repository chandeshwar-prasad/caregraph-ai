import pytest
from langgraph.types import Command
from app.database import SessionLocal
from app import crud, models
from app.services.scheduling import search_available_slots, book_appointment_slot, cancel_appointment_slot
from app.services.graph import graph


def test_synthetic_slot_search():
    """Verify synthetic slot provider returns realistic mock slots clearly labeled as demo data."""
    slots = search_available_slots("dermatologist", "tomorrow")
    assert len(slots) > 0
    assert "Alex Smith" in slots[0]["doctor_name"]
    assert slots[0]["is_mock"] is True
    assert slots[0]["source_name"] == "Mock Demo Availability Provider"


def test_scheduling_approval_creates_db_record():
    """Verify approving a scheduling request creates exactly one verified DB Appointment record."""
    session_id = "test_sched_db_app_1"
    config = {"configurable": {"thread_id": session_id}}
    
    # 1. Trigger scheduling interrupt
    graph.invoke({
        "user_message": "Schedule a visit with cardiologist next week",
        "user_id": 1,
        "session_id": session_id
    }, config=config)
    
    # 2. Resume with Approval
    res_state = graph.invoke(Command(resume={"approval_status": "approved"}), config=config)
    assert res_state["approval_status"] == "approved"
    assert res_state["appointment_id"] is not None
    
    # 3. Verify in database
    db = SessionLocal()
    try:
        apt = db.query(models.Appointment).filter(models.Appointment.id == res_state["appointment_id"]).first()
        assert apt is not None
        assert apt.patient_id == 1
        assert apt.status == "scheduled"
        assert apt.doctor_name is not None
        assert apt.specialty is not None

    finally:
        db.close()


def test_scheduling_rejection_no_db_record():
    """Verify rejecting a scheduling request performs ZERO database mutation."""
    session_id = "test_sched_db_rej_1"
    config = {"configurable": {"thread_id": session_id}}
    
    # Get initial appointment count for patient 1
    db = SessionLocal()
    initial_count = db.query(models.Appointment).filter(models.Appointment.patient_id == 1).count()
    db.close()

    # 1. Trigger scheduling interrupt
    graph.invoke({
        "user_message": "Book an appointment with neurologist tomorrow",
        "user_id": 1,
        "session_id": session_id
    }, config=config)
    
    # 2. Resume with Rejection
    res_state = graph.invoke(Command(resume={"approval_status": "rejected"}), config=config)
    assert res_state["approval_status"] == "rejected"
    
    # 3. Verify DB count remains unchanged
    db = SessionLocal()
    final_count = db.query(models.Appointment).filter(models.Appointment.patient_id == 1).count()
    db.close()
    assert final_count == initial_count


def test_red_flag_bypasses_scheduling():
    """Verify emergency red-flag symptoms during a scheduling request force immediate emergency escalation."""
    session_id = "test_sched_redflag_1"
    config = {"configurable": {"thread_id": session_id}}
    
    res_state = graph.invoke({
        "user_message": "I need to schedule an appointment because I have severe chest pain and trouble breathing",
        "user_id": 1,
        "session_id": session_id
    }, config=config)
    
    assert res_state["safety_escalated"] is True
    assert res_state["risk_level"] == "emergency"
    assert "EMERGENCY SAFETY ESCALATION DETECTED" in res_state["final_response"]


def test_get_my_appointments_and_cancellation_flow():
    """Verify GET /appointments/me, POST /appointments/{id}/cancel, patient isolation, and already-cancelled safety."""
    from fastapi.testclient import TestClient
    from app.main import app
    test_client = TestClient(app)

    # 1. Login Patient A
    login_a = test_client.post("/auth/login", data={"username": "hitl_patient_a", "password": "hitl_password_a"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Login Patient B
    login_b = test_client.post("/auth/login", data={"username": "hitl_patient_b", "password": "hitl_password_b"})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Schedule an appointment for Patient A via chat
    sess_a = "sess_ep_sched_1"
    test_client.post("/chat", json={"message": "Book dermatologist appointment tomorrow", "session_id": sess_a}, headers=headers_a)
    test_client.post("/chat/approve", json={"session_id": sess_a, "decision": "approved"}, headers=headers_a)

    # 4. Patient A retrieves appointments via GET /appointments/me
    get_res_a = test_client.get("/appointments/me", headers=headers_a)
    assert get_res_a.status_code == 200
    apts_a = get_res_a.json()
    assert len(apts_a) > 0
    apt_id_a = apts_a[0]["id"]
    assert apts_a[0]["status"] == "scheduled"

    # 5. Patient Isolation: Patient B retrieves their own appointments -> should not see Patient A's appointment
    get_res_b = test_client.get("/appointments/me", headers=headers_b)
    assert get_res_b.status_code == 200
    apts_b = get_res_b.json()
    b_ids = [apt["id"] for apt in apts_b]
    assert apt_id_a not in b_ids

    # 6. Patient Isolation: Patient B attempts to cancel Patient A's appointment -> 404 Not Found
    cross_cancel = test_client.post(f"/appointments/{apt_id_a}/cancel", headers=headers_b)
    assert cross_cancel.status_code == 404

    # 7. Nonexistent appointment cancellation -> 404 Not Found
    bad_cancel = test_client.post("/appointments/99999/cancel", headers=headers_a)
    assert bad_cancel.status_code == 404

    # 8. Patient A cancels their own appointment -> 200 OK
    cancel_res = test_client.post(f"/appointments/{apt_id_a}/cancel", headers=headers_a)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 9. Cancelling an already-cancelled appointment handles safely -> 200 OK with status="cancelled"
    recancel_res = test_client.post(f"/appointments/{apt_id_a}/cancel", headers=headers_a)
    assert recancel_res.status_code == 200
    assert recancel_res.json()["status"] == "cancelled"

