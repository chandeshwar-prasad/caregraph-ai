import pytest
from app import models, crud
from app.database import SessionLocal, engine
from app.services.graph import graph
from app.services.knowledge import get_grounded_knowledge
from app.services.triage import build_triage_response

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    crud.seed_initial_data(db)
    from app.services.vector_store import index_all_unindexed_documents
    index_all_unindexed_documents(db)
    yield db
    db.close()

def test_triage_graph_with_vector_grounding(setup_db):
    """1. LangGraph triage node performs vector retrieval and populates retrieved_sources."""
    initial_state = {
        "user_message": "I have been experiencing a high fever and chills",
        "user_id": 1,
        "session_id": "test_rag_fever"
    }
    config = {"configurable": {"thread_id": "test_rag_fever"}}
    result = graph.invoke(initial_state, config=config)

    assert result["current_agent"] == "triage"
    assert result["safety_escalated"] is False
    assert len(result["retrieved_sources"]) > 0

    top_source = result["retrieved_sources"][0]
    assert "title" in top_source
    assert "source_name" in top_source
    assert "version" in top_source
    assert "similarity_score" in top_source
    assert "Fever" in top_source["title"]

def test_triage_graph_source_attribution_in_response(setup_db):
    """2. Triage response includes care guidance and non-diagnostic disclaimers."""
    initial_state = {
        "user_message": "I have a painful sore throat and difficulty swallowing",
        "user_id": 1,
        "session_id": "test_rag_throat"
    }
    config = {"configurable": {"thread_id": "test_rag_throat"}}
    result = graph.invoke(initial_state, config=config)

    final_resp = result["final_response"]
    assert "not a doctor" in final_resp.lower()
    assert len(result["retrieved_sources"]) > 0
    assert len(result["follow_up_questions"]) == 3

def test_triage_low_confidence_fallback_safety(setup_db):
    """3. Unmatched/low-confidence symptom queries safely return general monitoring guidance without hallucinations."""
    initial_state = {
        "user_message": "I have an unexplained symptom with mild ache in my left toe",
        "user_id": 1,
        "session_id": "test_rag_unmatched"
    }
    config = {"configurable": {"thread_id": "test_rag_unmatched"}}
    result = graph.invoke(initial_state, config=config)

    assert result["current_agent"] == "triage"
    assert result["safety_escalated"] is False
    final_resp = result["final_response"].lower()
    assert "not a doctor" in final_resp
    assert "monitor your condition" in final_resp or "care navigation" in final_resp
    assert "i prescribe" not in final_resp

def test_emergency_safety_precedence_over_rag(setup_db):
    """4. Red-flag life-threatening emergency bypasses RAG and vector retrieval completely."""
    initial_state = {
        "user_message": "I have crushing chest pain and shortness of breath",
        "user_id": 1,
        "session_id": "test_rag_emergency"
    }
    config = {"configurable": {"thread_id": "test_rag_emergency"}}
    result = graph.invoke(initial_state, config=config)

    assert result["safety_escalated"] is True
    assert result["risk_level"] == "emergency"
    assert "EMERGENCY SAFETY ESCALATION DETECTED" in result["final_response"]
    assert "911" in result["final_response"]
