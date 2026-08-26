"""
app/services/vector_store.py

Vector store and semantic search service layer for CareGraph AI Phase 7 (pgvector & RAG).
Supports pgvector cosine distance on PostgreSQL and vector dot-product similarity fallback on SQLite.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session
from app import models
from app.services.embeddings import get_embedding_service


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def search_similar_documents(
    db: Session,
    query: str,
    top_k: int = 3,
    category: Optional[str] = None,
    status: str = "active",
    min_similarity: float = 0.1
) -> List[Dict[str, Any]]:
    """
    Perform semantic vector similarity search against knowledge documents.
    Applies status and category metadata filtering before ranking.
    """
    if not query or not query.strip():
        return []

    embedding_service = get_embedding_service()
    query_vector = embedding_service.get_embedding(query)

    # Base query with metadata filtering
    query_builder = db.query(models.KnowledgeDocument)
    if status:
        query_builder = query_builder.filter(models.KnowledgeDocument.status == status)
    if category:
        query_builder = query_builder.filter(models.KnowledgeDocument.category == category)

    docs = query_builder.all()
    if not docs:
        return []

    scored_docs = []
    for doc in docs:
        # If document lacks an embedding, generate one on-the-fly
        if doc.embedding is None:
            doc_text = f"{doc.title} {doc.content}"
            doc_vec = embedding_service.get_embedding(doc_text)
            doc.embedding = doc_vec
            db.commit()
            db.refresh(doc)
        else:
            # Handle list or ndarray format from database
            doc_vec = list(doc.embedding) if hasattr(doc.embedding, "__iter__") else doc.embedding

        similarity = compute_cosine_similarity(query_vector, doc_vec)
        if similarity >= min_similarity:
            scored_docs.append((similarity, doc))

    # Sort descending by similarity score
    scored_docs.sort(key=lambda item: item[0], reverse=True)

    results = []
    for score, doc in scored_docs[:top_k]:
        results.append({
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "source": doc.source,
            "source_type": doc.source_type,
            "category": doc.category,
            "version": doc.version,
            "status": doc.status,
            "region": doc.region,
            "publication_date": doc.publication_date,
            "similarity_score": round(score, 4)
        })

    return results


def index_knowledge_document(db: Session, doc_id: int) -> Optional[models.KnowledgeDocument]:
    """Generate and store embedding for a specific knowledge document."""
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == doc_id).first()
    if not doc:
        return None

    embedding_service = get_embedding_service()
    doc_text = f"{doc.title} {doc.content}"
    doc.embedding = embedding_service.get_embedding(doc_text)
    db.commit()
    db.refresh(doc)
    return doc


def index_all_unindexed_documents(db: Session) -> int:
    """Index all knowledge documents in the database that currently lack embeddings."""
    all_docs = db.query(models.KnowledgeDocument).all()
    unindexed = [d for d in all_docs if d.embedding is None or d.embedding == "null"]
    if not unindexed:
        return 0

    embedding_service = get_embedding_service()
    for doc in unindexed:
        doc_text = f"{doc.title} {doc.content}"
        doc.embedding = embedding_service.get_embedding(doc_text)
    db.commit()
    return len(unindexed)
