"""Tool Memory subsystem.

Tracks per-tool performance metadata (success rate, latency, failures).
Stored as a simple JSON file.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from app.tracing import get_tracker

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "tool_stats.json"
)

_STATS: dict[str, Any] = {}
_LOADED = False


def _load_stats():
    global _STATS, _LOADED
    if _LOADED:
        return
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    if os.path.exists(_DB_PATH):
        try:
            with open(_DB_PATH, "r", encoding="utf-8") as f:
                _STATS = json.load(f)
        except Exception as e:
            logger.error("tool_memory: Failed to load stats: %s", e)
    _LOADED = True


def _save_stats():
    try:
        with open(_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(_STATS, f, indent=2)
    except Exception as e:
        logger.error("tool_memory: Failed to save stats: %s", e)


def record_tool_use(
    tool_name: str,
    success: bool,
    latency_ms: int,
    error: str | None = None,
) -> None:
    """Record a tool execution for stats tracking."""
    _load_stats()

    if tool_name not in _STATS:
        _STATS[tool_name] = {
            "invocations": 0,
            "successes": 0,
            "failures": 0,
            "total_latency_ms": 0,
            "common_errors": {},
            "last_used": 0,
        }

    stat = _STATS[tool_name]
    stat["invocations"] += 1
    stat["last_used"] = time.time()
    stat["total_latency_ms"] += latency_ms

    if success:
        stat["successes"] += 1
    else:
        stat["failures"] += 1
        if error:
            err_key = error[:30] + "..." if len(error) > 30 else error
            stat["common_errors"][err_key] = stat["common_errors"].get(err_key, 0) + 1

    _save_stats()

    tracker = get_tracker()
    if tracker:
        tracker.track_memory_op(
            op_type="Record Tool Stats",
            category_or_key=tool_name,
            payload={"success": success, "latency_ms": latency_ms, "error": error},
        )


def get_tool_stats(tool_name: str) -> dict[str, Any]:
    """Get performance statistics for a specific tool."""
    _load_stats()
    stat = _STATS.get(tool_name, {})
    if not stat:
        return {"success_rate": 1.0, "avg_latency_ms": 0, "invocations": 0}

    invocations = stat["invocations"]
    return {
        "success_rate": stat["successes"] / invocations if invocations else 1.0,
        "avg_latency_ms": stat["total_latency_ms"] / invocations if invocations else 0,
        "invocations": invocations,
        "failures": stat["failures"],
    }


def get_all_tool_stats() -> dict[str, dict]:
    """Get all tool statistics."""
    _load_stats()
    return {
        name: get_tool_stats(name)
        for name in _STATS.keys()
    }


def get_best_tool_for(capability: str) -> str:
    """Recommend the most reliable tool for a given capability."""
    return capability
