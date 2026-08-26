"""
app/services/embeddings.py

Embedding service layer for CareGraph AI Phase 7 (pgvector & RAG).
Produces 384-dimensional unit-normalized dense vectors for clinical documents and queries.
"""

from abc import ABC, abstractmethod
from typing import List
import hashlib
import numpy as np


class BaseEmbeddingService(ABC):
    """Abstract base class for text embedding models."""
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension size."""
        pass

    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Generate a dense vector embedding for input text."""
        pass

    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate dense vector embeddings for a list of text strings."""
        pass


class DeterministicHealthcareEmbeddingService(BaseEmbeddingService):
    """
    Deterministic 384-dimensional embedding generator.
    Produces unit-normalized dense vectors using namespaced token, stem, and bigram feature projections.
    Ensures exact 384-dimension consistency across document ingestion and query retrieval.
    """

    STOP_WORDS = {
        "the", "and", "with", "for", "that", "from", "this", "have", "are",
        "not", "you", "your", "was", "can", "will", "been", "has", "about",
        "into", "more", "over", "some", "such", "than", "then", "very"
    }

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _text_to_vector(self, text: str) -> np.ndarray:
        """Map text tokens, stems, and bigrams deterministically into a 384-dim dense float vector."""
        vec = np.zeros(self._dimension, dtype=np.float32)
        if not text or not text.strip():
            return vec

        cleaned = text.lower().replace("-", " ").replace("/", " ")
        raw_words = [w.strip(".,!?:;\"'()[]{}") for w in cleaned.split()]
        words = [w for w in raw_words if len(w) > 1 and w not in self.STOP_WORDS]

        for i, word in enumerate(words):
            # 1. Exact full word hash (high weight)
            h1 = int(hashlib.sha256(f"w_{word}".encode("utf-8")).hexdigest(), 16)
            vec[h1 % self._dimension] += 5.0

            # 2. 4-char prefix stem
            if len(word) >= 4:
                stem = word[:4]
                h2 = int(hashlib.sha256(f"s_{stem}".encode("utf-8")).hexdigest(), 16)
                vec[h2 % self._dimension] += 2.0

            # 3. Bigram
            if i < len(words) - 1:
                bigram = f"{word}_{words[i+1]}"
                h3 = int(hashlib.sha256(f"b_{bigram}".encode("utf-8")).hexdigest(), 16)
                vec[h3 % self._dimension] += 3.0

        # L2 Normalization to unit length
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def get_embedding(self, text: str) -> List[float]:
        vec = self._text_to_vector(text)
        return vec.tolist()

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embedding(t) for t in texts]


# Singleton instance
_embedding_service_instance: BaseEmbeddingService = DeterministicHealthcareEmbeddingService(dimension=384)


def get_embedding_service() -> BaseEmbeddingService:
    """Return configured embedding service instance (384 dimensions)."""
    return _embedding_service_instance
