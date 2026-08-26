import pytest
from app import models, crud, schemas_ai
from app.database import SessionLocal, engine

@pytest.fixture(scope="module")
def db_session():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    crud.seed_initial_data(db)
    yield db
    db.close()

def test_knowledge_document_seeding(db_session):
    docs = crud.get_knowledge_documents(db_session)
    assert len(docs) >= 5
    titles = [d.title for d in docs]
    assert any("Fever" in t for t in titles)
    assert any("Cough" in t for t in titles)
    assert any("Headache" in t for t in titles)

def test_knowledge_document_metadata_fields(db_session):
    fever_doc = db_session.query(models.KnowledgeDocument).filter(
        models.KnowledgeDocument.title.like("%Fever%")
    ).first()
    assert fever_doc is not None
    assert fever_doc.source == "CareGraph Curated Care Navigation Summary"
    assert fever_doc.source_type == "clinical_guideline"
    assert fever_doc.category == "triage"
    assert fever_doc.version == "v1.0"
    assert fever_doc.status == "active"
    assert fever_doc.region == "US"
    assert fever_doc.publication_date == "2026-01-01"
    assert fever_doc.ingestion_date is not None

def test_create_and_retrieve_knowledge_document_with_embedding(db_session):
    dummy_embedding = [0.01 * i for i in range(384)]
    doc = crud.create_knowledge_document(
        db=db_session,
        title="Hypertension Care Navigation",
        content="Monitor resting blood pressure regularly and reduce sodium intake.",
        source="American Heart Association Summary",
        source_type="clinical_guideline",
        category="cardiology",
        version="v1.1",
        status="active",
        region="US",
        publication_date="2026-02-01",
        embedding=dummy_embedding
    )
    assert doc.id is not None
    assert doc.title == "Hypertension Care Navigation"
    assert doc.category == "cardiology"
    assert doc.embedding is not None

    retrieved = crud.get_knowledge_document_by_id(db_session, doc.id)
    assert retrieved is not None
    assert retrieved.title == "Hypertension Care Navigation"

def test_knowledge_document_status_filtering(db_session):
    # Create stale and superseded documents
    stale_doc = crud.create_knowledge_document(
        db=db_session,
        title="Outdated Flu Protocol 2020",
        content="Archived protocol content.",
        source="CDC Archive",
        category="triage",
        version="v0.9",
        status="stale"
    )
    superseded_doc = crud.create_knowledge_document(
        db=db_session,
        title="Superseded Triage Protocol",
        content="Superseded content.",
        source="CDC Archive",
        category="triage",
        version="v1.0",
        status="superseded"
    )

    active_docs = crud.get_knowledge_documents(db_session, status="active")
    active_ids = [d.id for d in active_docs]
    assert stale_doc.id not in active_ids
    assert superseded_doc.id not in active_ids

    stale_docs = crud.get_knowledge_documents(db_session, status="stale")
    assert any(d.id == stale_doc.id for d in stale_docs)
