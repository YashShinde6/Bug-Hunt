"""Embedding Service — sentence-transformers for bug text embeddings."""
import hashlib
import numpy as np
from typing import Optional


class EmbeddingService:
    """Generate embeddings for bug description text."""

    def __init__(self):
        self._model = None
        self._dimension = 384  # all-MiniLM-L6-v2 dimension

    def _load_model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                self._model = "fallback"
            except Exception:
                self._model = "fallback"

    def encode(self, text: str) -> list[float]:
        """Encode text into a vector embedding."""
        self._load_model()

        if self._model == "fallback":
            return self._fallback_embedding(text)

        try:
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception:
            return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str) -> list[float]:
        """Simple hash-based fallback when model is unavailable."""
        hash_bytes = hashlib.sha384(text.encode()).digest()
        # Convert to floats in [-1, 1] range
        values = [((b - 128) / 128.0) for b in hash_bytes]
        return values

    @property
    def dimension(self) -> int:
        return self._dimension
