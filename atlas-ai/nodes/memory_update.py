"""Memory Update node.

After a session completes (or at the end of any planning run), extracts and
stores user preferences, tool performance data, and episodic summaries.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from graph.state import TripState
from memory.tool_memory import record_tool_use, get_all_tool_stats
from memory.episodic_memory import store_episode
from memory.user_memory import store_preference

logger = logging.getLogger(__name__)


def memory_update(state: TripState) -> dict[str, Any]:
    """Extract and persist session data to the memory subsystem."""

    user_id = "default_user"  # TODO: extract from auth when available
    parsed_goal = state.get("parsed_goal", {})

    # --- 1. Record tool performance ---
    tool_results = state.get("tool_results", {})
    errors = state.get("errors", [])
    failed_tools = {e.get("tool") for e in errors if e.get("tool")}

    for tool_name in tool_results:
        success = tool_name not in failed_tools
        record_tool_use(
            tool_name=tool_name,
            success=success,
            latency_ms=0,  # Latency tracking would be added at dispatch time
            error=None,
        )

    for err in errors:
        tool_name = err.get("tool", "unknown")
        record_tool_use(
            tool_name=tool_name,
            success=False,
            latency_ms=0,
            error=err.get("error", "Unknown error"),
        )

    # --- 2. Extract and store user preferences ---
    preferences_learned = []

    # Destination preference
    destination = parsed_goal.get("destination")
    if destination:
        pref = f"Traveled to {destination}"
        store_preference(
            user_id=user_id,
            category="destinations_visited",
            preference=pref,
            metadata={"destination": destination},
        )
        preferences_learned.append(pref)

    # Budget pattern
    budget = parsed_goal.get("budget")
    currency = parsed_goal.get("currency", "INR")
    if budget:
        pref = f"Budget of {budget} {currency} for {parsed_goal.get('days', '?')} days"
        store_preference(
            user_id=user_id,
            category="budget",
            preference=pref,
            metadata={"budget": budget, "currency": currency},
        )
        preferences_learned.append(pref)

    # Food preferences
    for constraint in parsed_goal.get("constraints", []):
        if any(word in constraint.lower() for word in ["food", "vegetarian", "vegan", "halal"]):
            store_preference(
                user_id=user_id,
                category="food",
                preference=constraint,
                metadata={},
            )
            preferences_learned.append(constraint)

    # --- 3. Store episodic memory ---
    episode = {
        "user_id": user_id,
        "destination": destination or "Unknown",
        "dates": f"{parsed_goal.get('start_date', '?')} to {parsed_goal.get('end_date', '?')}",
        "budget": budget,
        "plan_summary": state.get("evaluation_reasoning", "No summary available."),
        "satisfaction_score": 1.0 if state.get("goal_satisfied", False) else 0.5,
        "lessons_learned": [
            f.get("reasoning", "")
            for f in state.get("failure_history", [])
            if f.get("reasoning")
        ],
        "timestamp": time.time(),
    }
    store_episode(episode)

    # --- 4. Build session summary ---
    session_summary = {
        "destination": destination,
        "goal_satisfied": state.get("goal_satisfied", False),
        "iterations": state.get("planner_iteration", 0),
        "sub_goals_count": len(state.get("sub_goals", [])),
        "tools_used": list(tool_results.keys()),
        "errors_encountered": len(errors),
        "recovery_attempts": state.get("recovery_attempts", 0),
        "preferences_learned": preferences_learned,
    }

    logger.info("memory_update: Session persisted. Preferences=%d", len(preferences_learned))

    return {
        "memory_context": {
            **state.get("memory_context", {}),
            "preferences_learned": preferences_learned,
        },
        "session_summary": session_summary,
        "tool_stats": get_all_tool_stats(),
    }
