import pytest
import numpy as np
from app import models, crud
from app.database import SessionLocal, engine
from app.services.embeddings import get_embedding_service, DeterministicHealthcareEmbeddingService
from app.services.vector_store import (
    search_similar_documents,
    compute_cosine_similarity,
    index_knowledge_document,
    index_all_unindexed_documents
)

@pytest.fixture(scope="module")
def db_session():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    crud.seed_initial_data(db)
    # Ensure all initial seeded documents have embeddings
    index_all_unindexed_documents(db)
    yield db
    db.close()

def test_embedding_service_exact_384_dimensions():
    service = get_embedding_service()
    assert service.dimension == 384

    text = "Patient presenting with high fever and chills."
    emb = service.get_embedding(text)
    assert isinstance(emb, list)
    assert len(emb) == 384
    for val in emb:
        assert isinstance(val, float)

def test_embedding_service_unit_normalization():
    service = get_embedding_service()
    text = "Mild persistent cough with sore throat."
    emb = service.get_embedding(text)
    norm = np.linalg.norm(np.array(emb))
    assert pytest.approx(norm, abs=1e-5) == 1.0

def test_embedding_service_deterministic_reproducibility():
    service = get_embedding_service()
    text = "Headache and photophobia management guidelines."
    emb1 = service.get_embedding(text)
    emb2 = service.get_embedding(text)
    assert emb1 == emb2

def test_cosine_similarity_calculation():
    service = get_embedding_service()
    emb_fever = service.get_embedding("High fever and elevated temperature")
    emb_fever2 = service.get_embedding("Fever and body warmth")
    emb_unrelated = service.get_embedding("Schedule dental checkup on Tuesday")

    sim_related = compute_cosine_similarity(emb_fever, emb_fever2)
    sim_unrelated = compute_cosine_similarity(emb_fever, emb_unrelated)

    assert sim_related > sim_unrelated
    assert -1.0 <= sim_related <= 1.0

def test_vector_search_fever_query(db_session):
    results = search_similar_documents(
        db=db_session,
        query="I have a high fever and body temperature over 101",
        top_k=2,
        status="active"
    )
    assert len(results) > 0
    top_result = results[0]
    assert "Fever" in top_result["title"]
    assert top_result["category"] == "triage"
    assert top_result["similarity_score"] > 0.2

def test_vector_search_cough_query(db_session):
    results = search_similar_documents(
        db=db_session,
        query="Persistent dry cough that won't stop for days",
        top_k=2,
        status="active"
    )
    assert len(results) > 0
    top_result = results[0]
    assert "Cough" in top_result["title"]

def test_vector_search_headache_query(db_session):
    results = search_similar_documents(
        db=db_session,
        query="Severe throbbing headache in dark room",
        top_k=2,
        status="active"
    )
    assert len(results) > 0
    top_result = results[0]
    assert "Headache" in top_result["title"]

def test_vector_search_metadata_status_filtering(db_session):
    # Insert a stale guideline
    emb_service = get_embedding_service()
    stale_doc = models.KnowledgeDocument(
        title="Archived Obsolete Fever Protocol",
        content="Old fever advice from 2010.",
        source="CDC Archive",
        source_type="clinical_guideline",
        category="triage",
        version="v0.1",
        status="stale",
        embedding=emb_service.get_embedding("Old fever advice from 2010.")
    )
    db_session.add(stale_doc)
    db_session.commit()

    # Search active only
    active_results = search_similar_documents(
        db=db_session,
        query="fever protocol",
        top_k=5,
        status="active"
    )
    active_ids = [r["id"] for r in active_results]
    assert stale_doc.id not in active_ids

    # Search stale only
    stale_results = search_similar_documents(
        db=db_session,
        query="fever protocol",
        top_k=5,
        status="stale"
    )
    stale_ids = [r["id"] for r in stale_results]
    assert stale_doc.id in stale_ids

def test_vector_store_indexing_functions(db_session):
    # Create doc without embedding
    doc = models.KnowledgeDocument(
        title="Dermatology Skin Hydration Guideline",
        content="Apply gentle emollient lotions to dry skin.",
        source="Dermatology Society",
        source_type="clinical_guideline",
        category="dermatology",
        version="v1.0",
        status="active",
        embedding=None
    )
    db_session.add(doc)
    db_session.commit()
    assert doc.embedding is None

    # Test single document indexer
    indexed_doc = index_knowledge_document(db_session, doc.id)
    assert indexed_doc is not None
    assert indexed_doc.embedding is not None
    assert len(list(indexed_doc.embedding)) == 384

    # Create another doc without embedding
    doc2 = models.KnowledgeDocument(
        title="Pediatric Hydration Guideline",
        content="Oral rehydration solution guidance for infants.",
        source="Pediatric Society",
        source_type="clinical_guideline",
        category="pediatrics",
        version="v1.0",
        status="active",
        embedding=None
    )
    db_session.add(doc2)
    db_session.commit()

    # Test batch indexer
    count = index_all_unindexed_documents(db_session)
    assert count >= 1

    # Second run should find 0 unindexed
    count2 = index_all_unindexed_documents(db_session)
    assert count2 == 0
