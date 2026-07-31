"""User memory subsystem.

Stores and retrieves long-term user preferences using ChromaDB for semantic search.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None

logger = logging.getLogger(__name__)

# Singleton client
_CLIENT = None
_COLLECTION_NAME = "user_preferences"


def _get_collection():
    """Get or create the ChromaDB collection for user preferences."""
    global _CLIENT
    if chromadb is None:
        logger.warning("user_memory: chromadb not installed, falling back to mock memory.")
        return None

    if _CLIENT is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chromadb")
        os.makedirs(db_path, exist_ok=True)
        _CLIENT = chromadb.PersistentClient(path=db_path)

    return _CLIENT.get_or_create_collection(name=_COLLECTION_NAME)


def store_preference(
    user_id: str,
    category: str,
    preference: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Store a learned user preference.

    Parameters
    ----------
    user_id : str
        The ID of the user.
    category : str
        Category (e.g., 'food', 'budget', 'airlines').
    preference : str
        The raw text preference (e.g., 'Prefers window seats on flights').
    metadata : dict, optional
        Additional structured data to store.
    """
    collection = _get_collection()
    if not collection:
        logger.warning(f"Mock storing preference: {preference} for user {user_id}")
        return

    doc_id = str(uuid.uuid4())
    meta = {"user_id": user_id, "category": category}
    if metadata:
        # Chroma metadata values must be strings, ints, or floats
        for k, v in metadata.items():
            if isinstance(v, (dict, list)):
                meta[k] = json.dumps(v)
            else:
                meta[k] = v

    collection.add(
        documents=[preference],
        metadatas=[meta],
        ids=[doc_id],
    )
    logger.info("user_memory: Stored preference for %s: %s", user_id, preference)


def retrieve_preferences(user_id: str, query: str, n_results: int = 5) -> list[dict]:
    """Retrieve relevant user preferences using semantic search.

    Parameters
    ----------
    user_id : str
        The ID of the user.
    query : str
        The semantic query (e.g., 'What kind of food do they like?').
    n_results : int, default=5
        Number of results to return.

    Returns
    -------
    list[dict]
        List of matching preferences with metadata.
    """
    collection = _get_collection()
    if not collection:
        logger.warning("Mock retrieving preferences, returning empty.")
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"user_id": user_id},
        )
    except Exception as e:
        logger.error(f"user_memory: Failed to query ChromaDB: {e}")
        return []

    preferences = []
    if results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        for doc, meta in zip(docs, metas):
            preferences.append({
                "preference": doc,
                "category": meta.get("category", "general"),
                "metadata": meta,
            })

    return preferences
