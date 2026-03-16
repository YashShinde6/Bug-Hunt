"""Pinecone Service — vector database for bug context storage and retrieval."""
import uuid
from typing import Optional

from config import settings


class PineconeService:
    """Interface to Pinecone vector database."""

    def __init__(self):
        self._index = None
        self._connected = False
        self._local_store: list[dict] = []  # Fallback in-memory store
        self._init_pinecone()

    def _init_pinecone(self):
        """Initialize Pinecone connection."""
        if not settings.has_pinecone:
            return

        try:
            from pinecone import Pinecone

            pc = Pinecone(api_key=settings.PINECONE_API_KEY)

            # Check if index exists
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if settings.PINECONE_INDEX_NAME not in existing_indexes:
                # Create index
                from pinecone import ServerlessSpec
                pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=384,  # all-MiniLM-L6-v2
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )

            self._index = pc.Index(settings.PINECONE_INDEX_NAME)
            self._connected = True

        except Exception as e:
            print(f"[PineconeService] Failed to connect: {e}")
            self._connected = False

    def upsert(self, vector: list[float], metadata: dict) -> str:
        """Store a bug context vector."""
        vec_id = str(uuid.uuid4())

        if self._connected and self._index:
            try:
                self._index.upsert(vectors=[(vec_id, vector, metadata)])
                return vec_id
            except Exception as e:
                print(f"[PineconeService] Upsert failed: {e}")

        # Fallback to local store
        self._local_store.append({
            "id": vec_id,
            "vector": vector,
            "metadata": metadata,
        })
        return vec_id

    def query(
        self,
        vector: list[float],
        top_k: int = 3,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """Query for similar bug contexts."""
        if self._connected and self._index:
            try:
                query_params = {
                    "vector": vector,
                    "top_k": top_k,
                    "include_metadata": True,
                }
                if filter_metadata:
                    query_params["filter"] = filter_metadata

                results = self._index.query(**query_params)
                return [
                    {**match.metadata, "score": match.score}
                    for match in results.matches
                ]
            except Exception as e:
                print(f"[PineconeService] Query failed: {e}")

        # Fallback: local cosine similarity
        return self._local_query(vector, top_k)

    def _local_query(self, vector: list[float], top_k: int) -> list[dict]:
        """Fallback local similarity search."""
        if not self._local_store:
            return []

        import numpy as np

        query_vec = np.array(vector)
        scores = []

        for item in self._local_store:
            stored_vec = np.array(item["vector"])
            # Cosine similarity
            denom = np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
            if denom > 0:
                sim = float(np.dot(query_vec, stored_vec) / denom)
            else:
                sim = 0.0
            scores.append((sim, item["metadata"]))

        scores.sort(key=lambda x: x[0], reverse=True)

        return [
            {**meta, "score": score}
            for score, meta in scores[:top_k]
            if score > 0.3  # Minimum similarity threshold
        ]
