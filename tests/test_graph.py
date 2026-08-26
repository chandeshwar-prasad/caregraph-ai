import pytest
from langgraph.types import Command
from app.services.graph import graph, CareGraphState, HealthSyncState
from app.schemas_ai import IntentEnum

def test_graph_compilation():
    """Verify that the LangGraph StateGraph compiles and has a checkpointer."""
    assert graph is not None
    assert graph.checkpointer is not None

def test_triage_routing():
    """Test routing a symptom query through the supervisor to the triage node."""
    initial_state = {
        "user_message": "I have a fever and bad cough since yesterday",
        "user_id": 1,
        "session_id": "test_session_triage"
    }
    config = {"configurable": {"thread_id": "test_session_triage"}}
    
    final_state = graph.invoke(initial_state, config=config)
    
    assert final_state["intent"] == IntentEnum.TRIAGE.value
    assert final_state["current_agent"] == "triage"
    assert final_state["approval_required"] is False
    assert "not a doctor" in final_state["final_response"].lower()

def test_emergency_routing():
    """Test routing an emergency query to the emergency safety node."""
    initial_state = {
        "user_message": "Help, chest pain and severe bleeding!",
        "user_id": 1,
        "session_id": "test_session_emergency"
    }
    config = {"configurable": {"thread_id": "test_session_emergency"}}
    
    final_state = graph.invoke(initial_state, config=config)
    
    assert final_state["risk_level"] == "emergency"
    assert final_state["safety_escalated"] is True
    assert "emergency" in final_state["final_response"].lower()


def test_scheduling_hitl_interrupt_and_resume():
    """
    Test the complete Scheduling HITL workflow:
    1. Send scheduling message -> graph dynamically interrupts on scheduling node
    2. Check checkpoint state -> confirms interrupt value payload
    3. Resume graph with Command(resume={'approval_status': 'approved'}) -> completes with approval response
    """
    session_id = "test_session_scheduling_hitl"
    config = {"configurable": {"thread_id": session_id}}
    
    initial_state = {
        "user_message": "I want to schedule an appointment with dermatologist tomorrow",
        "user_id": 1,
        "session_id": session_id
    }
    
    # 1. Invoke graph -> triggers dynamic interrupt() inside scheduling node
    graph.invoke(initial_state, config=config)
    
    # Verify snapshot state in checkpointer
    snapshot = graph.get_state(config)
    assert snapshot.next == ("scheduling",)
    assert len(snapshot.tasks) > 0
    interrupt_info = snapshot.tasks[0].interrupts[0].value
    assert interrupt_info["action"] == "approval_required"
    assert "confirm" in interrupt_info["message"].lower()
    
    # 2. Resume with User Approval using Command(resume=...)
    resumed_state = graph.invoke(
        Command(resume={"approval_status": "approved"}),
        config=config
    )
    
    assert resumed_state["approval_status"] == "approved"
    assert resumed_state["approval_required"] is False
    assert "confirmed" in resumed_state["final_response"].lower()
    assert "appointment id" in resumed_state["final_response"].lower()

def test_scheduling_hitl_rejection():
    """Test the Scheduling HITL rejection workflow."""
    session_id = "test_session_scheduling_reject"
    config = {"configurable": {"thread_id": session_id}}
    
    initial_state = {
        "user_message": "Book an appointment for doctor next wednesday",
        "user_id": 1,
        "session_id": session_id
    }
    
    graph.invoke(initial_state, config=config)
    
    # Reject the scheduling request using Command(resume=...)
    resumed_state = graph.invoke(
        Command(resume={"approval_status": "rejected"}),
        config=config
    )
    
    assert resumed_state["approval_status"] == "rejected"
    assert resumed_state["approval_required"] is False
    assert "rejected by user" in resumed_state["final_response"].lower()

def test_records_and_reminders_routing():
    """Test routing for records and reminders stubs."""
    # Records
    records_state = graph.invoke(
        {"user_message": "Show my blood pressure vitals history", "user_id": 1, "session_id": "rec_1"},
        config={"configurable": {"thread_id": "rec_1"}}
    )
    assert records_state["intent"] == IntentEnum.RECORDS.value
    assert records_state["current_agent"] == "records"
    
    # Reminders
    reminders_state = graph.invoke(
        {"user_message": "Remind me to take my medication at 8 PM", "user_id": 1, "session_id": "rem_1"},
        config={"configurable": {"thread_id": "rem_1"}}
    )
    assert reminders_state["intent"] == IntentEnum.REMINDERS.value
    assert reminders_state["current_agent"] == "reminders"
