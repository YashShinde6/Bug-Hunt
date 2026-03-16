"""RAG Agent — Pinecone-based bug history retrieval."""
from typing import Optional

from services.pinecone_service import PineconeService
from services.embedding_service import EmbeddingService

# Singletons
_embedding_service: Optional[EmbeddingService] = None
_pinecone_service: Optional[PineconeService] = None


def _get_services():
    global _embedding_service, _pinecone_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    if _pinecone_service is None:
        _pinecone_service = PineconeService()
    return _embedding_service, _pinecone_service


async def retrieve_similar_bugs(bugs: list[dict], language: str) -> list[dict]:
    """For each bug, retrieve similar historical bugs from Pinecone."""
    embedding_svc, pinecone_svc = _get_services()

    for bug in bugs:
        # Build text for embedding
        bug_text = _bug_to_text(bug, language)
        embedding = embedding_svc.encode(bug_text)

        # Query Pinecone — request extra to allow filtering
        similar = pinecone_svc.query(
            vector=embedding,
            top_k=6,
            filter_metadata={"language": language} if language else None,
        )

        # Filter and deduplicate results
        seen_explanations = set()
        unique_matches = []
        current_explanation = bug.get("explanation", "").lower().strip()

        for match in similar:
            score = match.get("score", 0)
            explanation = match.get("explanation", "").lower().strip()

            # Skip self-matches (exact same bug from same analysis)
            if score >= 0.99:
                continue

            # Skip duplicates with same explanation
            if explanation in seen_explanations:
                continue

            seen_explanations.add(explanation)
            unique_matches.append({
                "bug_type": match.get("bug_type", "Unknown"),
                "explanation": match.get("explanation", ""),
                "fix": match.get("fix", ""),
                "similarity": round(score * 100, 1),
            })

            if len(unique_matches) >= 3:
                break

        bug["historical_bugs"] = unique_matches

    return bugs


async def store_bugs(bugs: list[dict], language: str):
    """Store confirmed bugs in Pinecone for future retrieval."""
    embedding_svc, pinecone_svc = _get_services()

    for bug in bugs:
        bug_text = _bug_to_text(bug, language)
        embedding = embedding_svc.encode(bug_text)

        metadata = {
            "bug_type": bug.get("bug_type", "Unknown"),
            "language": language,
            "explanation": bug.get("explanation", "")[:500],
            "fix": bug.get("suggested_fix", "")[:500],
            "severity": bug.get("severity", "medium"),
            "impact": bug.get("impact", "")[:500],
        }

        pinecone_svc.upsert(
            vector=embedding,
            metadata=metadata,
        )


def _bug_to_text(bug: dict, language: str) -> str:
    """Convert a bug dict to a text string for embedding."""
    parts = [
        f"Bug Type: {bug.get('bug_type', 'Unknown')}",
        f"Language: {language}",
        f"Explanation: {bug.get('explanation', '')}",
        f"Impact: {bug.get('impact', '')}",
        f"Fix: {bug.get('suggested_fix', '')}",
    ]
    return " | ".join(parts)
