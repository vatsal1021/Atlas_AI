"""Semantic memory subsystem.

Stores general world knowledge learned across all sessions using ChromaDB.
"""

from __future__ import annotations

import logging
import os
import uuid

try:
    import chromadb
except ImportError:
    chromadb = None

logger = logging.getLogger(__name__)

_CLIENT = None
_COLLECTION_NAME = "semantic_knowledge"


def _get_collection():
    """Get or create the ChromaDB collection for semantic memory."""
    global _CLIENT
    if chromadb is None:
        return None

    if _CLIENT is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chromadb")
        os.makedirs(db_path, exist_ok=True)
        _CLIENT = chromadb.PersistentClient(path=db_path)

    return _CLIENT.get_or_create_collection(name=_COLLECTION_NAME)


def store_knowledge(fact: str, source: str, confidence: float = 1.0) -> None:
    """Store a piece of general world knowledge.

    Parameters
    ----------
    fact : str
        The knowledge fact (e.g., 'Shinjuku hotels are generally overpriced').
    source : str
        Where this fact came from (e.g., 'critic_node', 'user_feedback').
    confidence : float
        Confidence score (0.0 to 1.0).
    """
    collection = _get_collection()
    if not collection:
        logger.warning("Mock storing knowledge. ChromaDB not available.")
        return

    doc_id = f"fact_{uuid.uuid4().hex[:12]}"
    meta = {
        "source": source,
        "confidence": float(confidence),
    }

    collection.add(
        documents=[fact],
        metadatas=[meta],
        ids=[doc_id],
    )
    logger.info("semantic_memory: Stored fact.")


def recall_knowledge(query: str, n_results: int = 3) -> list[dict]:
    """Retrieve relevant world knowledge facts."""
    collection = _get_collection()
    if not collection:
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
        )
    except Exception as e:
        logger.error(f"semantic_memory: Query failed: {e}")
        return []

    facts = []
    if results and results["documents"]:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            facts.append({
                "fact": doc,
                "metadata": meta,
            })
    return facts
