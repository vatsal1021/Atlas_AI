"""Episodic memory subsystem.

Stores and retrieves summaries of past planning sessions using ChromaDB.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from app.tracing import get_tracker

try:
    import chromadb
except ImportError:
    chromadb = None

logger = logging.getLogger(__name__)

_CLIENT = None
_COLLECTION_NAME = "episodic_memory"


def _get_collection():
    """Get or create the ChromaDB collection for episodic memory."""
    global _CLIENT
    if chromadb is None:
        return None

    if _CLIENT is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chromadb")
        os.makedirs(db_path, exist_ok=True)
        _CLIENT = chromadb.PersistentClient(path=db_path)

    return _CLIENT.get_or_create_collection(name=_COLLECTION_NAME)


def store_episode(episode: dict) -> None:
    """Store a session summary."""
    tracker = get_tracker()
    if tracker:
        tracker.track_memory_op("Store Episode", episode.get("destination", "Trip"), episode)

    collection = _get_collection()
    if not collection:
        logger.warning("Mock storing episode. ChromaDB not available.")
        return

    doc_id = f"ep_{uuid.uuid4().hex[:12]}"
    content = f"Trip to {episode.get('destination')}. {episode.get('plan_summary')}\nLessons: {', '.join(episode.get('lessons_learned', []))}"
    
    meta = {
        "user_id": str(episode.get("user_id")),
        "destination": str(episode.get("destination")),
        "satisfaction_score": float(episode.get("satisfaction_score", 0.0)),
        "timestamp": float(episode.get("timestamp", 0.0)),
    }

    collection.add(
        documents=[content],
        metadatas=[meta],
        ids=[doc_id],
    )
    logger.info("episodic_memory: Stored episode %s", doc_id)


def recall_similar_trips(query: str, n_results: int = 3) -> list[dict]:
    """Find similar past trips based on semantic query."""
    collection = _get_collection()
    if not collection:
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
        )
    except Exception as e:
        logger.error(f"episodic_memory: Query failed: {e}")
        return []

    trips = []
    if results and results["documents"]:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            trips.append({
                "summary": doc,
                "metadata": meta,
            })

    tracker = get_tracker()
    if tracker:
        tracker.track_memory_op("Recall Trips", f"query:{query}", trips)

    return trips
