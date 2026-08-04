"""Conditional routing functions for the LangGraph state graph.

Each function takes a TripState and returns a string node name
that determines the next edge to follow.
"""

from __future__ import annotations

import logging

from graph.state import TripState
from app.settings import (
    ENABLE_REFLECTION,
    ENABLE_CRITIC,
    ENABLE_EXPLAINABILITY,
    ENABLE_HUMAN_APPROVAL,
)
from graph.edges import (
    EVIDENCE_AGGREGATOR,
    GOAL_EVALUATOR,
    GOAL_DECOMPOSITION,
    OBJECTIVE_PLANNER,
    CAPABILITY_DISPATCHER,
    WORLD_MODEL,
    REFLECTION,
    CRITIC,
    EXPLAINABILITY,
    HUMAN_APPROVAL,
    ACTION_DISPATCHER,
    META_REASONER,
    MEMORY_UPDATE,
)
from langgraph.graph import END

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: terminal routing — what comes after the QA / planning phase
# ---------------------------------------------------------------------------

def _terminal_route(state: TripState) -> str:
    """After the plan is complete, decide the next gate."""
    if ENABLE_HUMAN_APPROVAL:
        return HUMAN_APPROVAL
    return MEMORY_UPDATE


# ---------------------------------------------------------------------------
# Phase 1 / 2 routers
# ---------------------------------------------------------------------------


def route_after_evaluator(state: TripState) -> str:
    """Decide where to go after evaluation."""
    goal_satisfied = state.get("goal_satisfied", False)
    iteration = state.get("planner_iteration", 0)
    max_iter = state.get("max_iterations", 10)

    # Goal met OR max iterations reached → begin QA / terminal phase
    if goal_satisfied or iteration >= max_iter:
        if ENABLE_REFLECTION:
            return REFLECTION
        elif ENABLE_CRITIC:
            return CRITIC
        elif ENABLE_EXPLAINABILITY:
            return EXPLAINABILITY
        return _terminal_route(state)

    # Otherwise loop back to the planner for another iteration
    return OBJECTIVE_PLANNER


def route_after_reflection(state: TripState) -> str:
    """Route after reflection.

    If reflection found gaps and revisions remain, send back to planner.
    Otherwise hand off to critic / explainability / terminal gate.
    """
    has_gaps = bool(state.get("reflection_gaps", []))
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)

    if has_gaps and revision_count < max_revisions:
        return OBJECTIVE_PLANNER

    if ENABLE_CRITIC:
        return CRITIC
    elif ENABLE_EXPLAINABILITY:
        return EXPLAINABILITY
    return _terminal_route(state)


def route_after_critic(state: TripState) -> str:
    """Route after critic.

    If critic flagged revisions and we have budget left, send back to planner.
    Otherwise proceed to explainability / terminal gate.
    """
    should_revise = state.get("critic_should_revise", False)
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)

    if should_revise and revision_count < max_revisions:
        return OBJECTIVE_PLANNER

    if ENABLE_EXPLAINABILITY:
        return EXPLAINABILITY
    return _terminal_route(state)


# ---------------------------------------------------------------------------
# Phase 3 routers
# ---------------------------------------------------------------------------


def route_after_explainability(state: TripState) -> str:
    """Route after explainability. Go to approval or directly to memory update."""
    return _terminal_route(state)


def route_after_approval(state: TripState) -> str:
    """Route after human approval gate."""
    status = state.get("approval_status", "")
    if status == "rejected":
        return META_REASONER
    # approved or not_needed → execute actions
    return ACTION_DISPATCHER


def route_after_action_dispatcher(state: TripState) -> str:
    """Route after action dispatcher. If errors occurred, escalate to meta-reasoner."""
    if state.get("errors"):
        return META_REASONER
    return MEMORY_UPDATE


def route_after_meta_reasoning(state: TripState) -> str:
    """Route based on the recovery strategy chosen by the meta-reasoner."""
    history = state.get("failure_history", [])
    if not history:
        return END

    last_strategy = history[-1].get("strategy", "escalate")

    if last_strategy == "retry":
        return CAPABILITY_DISPATCHER
    elif last_strategy in ("alternative", "partial_replan"):
        return OBJECTIVE_PLANNER
    elif last_strategy == "full_replan":
        return GOAL_DECOMPOSITION

    # escalate → end the graph
    return END
