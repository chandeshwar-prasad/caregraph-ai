import pytest
from langgraph.types import Command
from app.services.graph import graph, CareGraphState, HealthSyncState
from app.schemas_ai import IntentEnum
from app.database import Base, engine, SessionLocal
from app import models, crud

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    crud.seed_initial_data(db)
    db.close()


def test_records_intent_routes_to_patient_data_node():
    state = graph.invoke(
        {"user_message": "Show my blood pressure vitals history", "user_id": 1, "session_id": "test_rec_node_1"},
        config={"configurable": {"thread_id": "test_rec_node_1"}}
    )
    assert state["intent"] == IntentEnum.RECORDS.value
    assert state["current_agent"] == "records"
    assert state["patient_data_tool"] in ["get_patient_vitals", "calculate_vital_trend"]
    assert state["patient_data_result"] is not None
    assert "Vital" in state["final_response"] or "120/80" in state["final_response"] or "Readings" in state["final_response"]


def test_reminders_intent_routes_to_patient_data_node():
    state = graph.invoke(
        {"user_message": "Show my medication reminders schedule", "user_id": 1, "session_id": "test_rem_node_1"},
        config={"configurable": {"thread_id": "test_rem_node_1"}}
    )
    assert state["intent"] == IntentEnum.REMINDERS.value
    assert state["current_agent"] == "reminders"
    assert state["patient_data_tool"] == "get_medication_schedule"
    assert state["patient_data_result"] is not None


def test_medications_retrieved_for_authenticated_patient():
    state = graph.invoke(
        {"user_message": "What medications am I taking?", "user_id": 1, "session_id": "test_med_node_1"},
        config={"configurable": {"thread_id": "test_med_node_1"}}
    )
    assert state["intent"] == IntentEnum.RECORDS.value
    assert state["patient_data_tool"] == "get_patient_medications"
    assert "Lisinopril" in state["final_response"]
    assert "Vitamin D3" in state["final_response"]


def test_vital_trend_graph_execution():
    state = graph.invoke(
        {"user_message": "Show my heart rate trend history over time", "user_id": 1, "session_id": "test_trend_node_1"},
        config={"configurable": {"thread_id": "test_trend_node_1"}}
    )
    assert state["intent"] == IntentEnum.RECORDS.value
    assert state["patient_data_tool"] == "calculate_vital_trend"
    assert state["patient_data_result"]["trend"] == "increasing"


def test_cross_patient_graph_isolation():
    db = SessionLocal()
    # User 2 (patient_b)
    user_b = crud.get_user_by_username(db, "patient_b")
    if not user_b:
        user_b = models.User(username="patient_b", password_hash="hash", role="patient")
        db.add(user_b)
        db.commit()
        db.refresh(user_b)
        patient_b = models.Patient(user_id=user_b.id, first_name="Bob", last_name="B")
        db.add(patient_b)
        db.commit()
    user_b_id = user_b.id
    db.close()

    # User 1 query
    state_a = graph.invoke(
        {"user_message": "Show my active medications", "user_id": 1, "session_id": "test_iso_a"},
        config={"configurable": {"thread_id": "test_iso_a"}}
    )
    # User 2 query
    state_b = graph.invoke(
        {"user_message": "Show my active medications", "user_id": user_b_id, "session_id": "test_iso_b"},
        config={"configurable": {"thread_id": "test_iso_b"}}
    )

    assert "Lisinopril" in state_a["final_response"]
    assert "Lisinopril" not in state_b["final_response"]
    assert "No active medications" in state_b["final_response"]


def test_red_flag_safety_precedence_with_records_query():
    state = graph.invoke(
        {"user_message": "Show my vitals, I have severe chest pain and bleeding", "user_id": 1, "session_id": "test_rf_rec_1"},
        config={"configurable": {"thread_id": "test_rf_rec_1"}}
    )
    assert state["safety_escalated"] is True
    assert state["risk_level"] == "emergency"
    assert state["current_agent"] == "emergency_safety"
    assert state.get("patient_data_tool") is None  # Never reached patient_data_node
