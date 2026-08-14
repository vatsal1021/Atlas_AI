"""Simple JSON-file-based user memory for Phase 1.

Stores and loads user preferences to/from ``data/user_memory.json``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from app.tracing import get_tracker

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MEMORY_FILE = _DATA_DIR / "user_memory.json"


def _ensure_file() -> None:
    """Create the data directory and memory file if they don't exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _MEMORY_FILE.exists():
        _MEMORY_FILE.write_text("{}", encoding="utf-8")


def load_preferences(user_id: str = "default") -> dict:
    """Load preferences for a user."""
    _ensure_file()
    try:
        data = json.loads(_MEMORY_FILE.read_text(encoding="utf-8"))
        prefs = data.get(user_id, {})
        logger.info("Loaded preferences for user=%s keys=%s", user_id, list(prefs.keys()))
        tracker = get_tracker()
        if tracker:
            tracker.track_memory_op("Load Preferences", f"user:{user_id}", prefs)
        return prefs
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load preferences: %s", exc)
        return {}


def save_preferences(user_id: str, prefs: dict) -> None:
    """Save preferences for a user."""
    _ensure_file()
    try:
        data = json.loads(_MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {}

    existing = data.get(user_id, {})
    existing.update(prefs)
    data[user_id] = existing

    _MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved preferences for user=%s", user_id)
    tracker = get_tracker()
    if tracker:
        tracker.track_memory_op("Save Preferences", f"user:{user_id}", prefs)
