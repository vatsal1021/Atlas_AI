"""CriticGate — Lightweight decision: should the Critic run?

Uses fast heuristics (no full LLM call) to decide whether the request/plan
is complex or high-risk enough to warrant a full CriticNode review.

Outputs critic_gate_decision: skip | critic_required
"""

from __future__ import annotations

import logging
from typing import Any

from graph.state import TripState
from app.settings import CRITIC_TRIGGER_TOOLS, CRITIC_REACT_ITERATION_THRESHOLD
from app.tracing import get_tracker

logger = logging.getLogger(__name__)


def critic_gate(state: TripState) -> dict[str, Any]:
    """Decide whether CriticNode should run based on heuristics."""
    tracker = get_tracker()

    observations = state.get("tool_observations", [])
    react_iter = state.get("react_iteration", 0)
    directive = state.get("planning_directive", {})
    errors = state.get("errors", [])

    tools_used = {obs.get("tool", "") for obs in observations}
    failed_tools = {obs.get("tool", "") for obs in observations if obs.get("status") == "error"}

    triggers = []

    # Trigger 1: irreversible tool was used
    if tools_used & CRITIC_TRIGGER_TOOLS:
        triggers.append("irreversible_tool_used")

    # Trigger 2: many ReAct iterations (complex request)
    if react_iter >= CRITIC_REACT_ITERATION_THRESHOLD:
        triggers.append("high_react_iterations")

    # Trigger 3: tool failures occurred
    if failed_tools:
        triggers.append("tool_failures")

    # Trigger 4: errors in state
    if errors:
        triggers.append("errors_present")

    # Trigger 5: multi-city / multi-leg clue in directive
    objective = str(directive.get("objective", "")).lower()
    if any(kw in objective for kw in ["multi", "cities", "countries", "legs", "complex"]):
        triggers.append("complex_objective")

    decision = "critic_required" if triggers else "skip"

    logger.info(
        "critic_gate: decision=%s  triggers=%s", decision, triggers
    )
    if tracker:
        tracker.log_trace(
            f"[CriticGate] decision={decision}"
            + (f"  triggers={triggers}" if triggers else "")
        )

    return {
        "critic_gate_decision": decision,
    }
