import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.vector_store import search_similar_documents

DATA_PATH = Path(__file__).parent.parent / "data" / "symptom_knowledge.json"


def get_grounded_knowledge(
    user_message: str,
    db: Optional[Session] = None,
    top_k: int = 3,
    min_similarity: float = 0.15
) -> List[Dict[str, Any]]:
    """
    Retrieves grounded clinical care navigation documents for user_message.
    1. Uses pgvector/vector similarity search if a db session is provided.
    2. Falls back to keyword matching over local curated knowledge if db is unavailable or returns 0 matches.
    """
    if db is not None:
        try:
            vector_results = search_similar_documents(
                db=db,
                query=user_message,
                top_k=top_k,
                status="active",
                min_similarity=min_similarity
            )
            if vector_results:
                matched = []
                for doc in vector_results:
                    matched.append({
                        "id": doc.get("id"),
                        "title": doc.get("title"),
                        "guidance": doc.get("content"),
                        "source_name": doc.get("source", "CareGraph Curated Care Navigation Summary"),
                        "source_type": doc.get("source_type", "clinical_guideline"),
                        "category": doc.get("category", "triage"),
                        "version": doc.get("version", "v1.0"),
                        "similarity_score": doc.get("similarity_score", 0.0)
                    })
                return matched
        except Exception:
            pass

    # Fallback to local JSON if db search is unavailable or returns empty
    if not DATA_PATH.exists():
        return []

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            entries: List[Dict[str, Any]] = json.load(f)
    except Exception:
        return []

    text_lower = user_message.lower()
    matched = []

    for entry in entries:
        key = entry.get("symptom_key", "").lower()
        if key and key in text_lower:
            matched.append({
                "symptom_key": entry.get("symptom_key"),
                "title": f"{entry.get('symptom_key', '').title()} Guidance",
                "guidance": entry.get("guidance"),
                "source_name": entry.get("source_name", "CareGraph Curated Care Navigation Summary"),
                "source_type": entry.get("source_type", "Curated Project Content"),
                "category": "triage",
                "version": "v1.0",
                "similarity_score": 1.0
            })

    return matched
