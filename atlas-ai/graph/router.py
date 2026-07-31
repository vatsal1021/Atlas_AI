"""Conditional routing functions for the LangGraph state graph.

Each function takes a TripState and returns a string node name
that determines the next edge to follow.
"""

from __future__ import annotations

import logging

from graph.state import TripState
from app.settings import ENABLE_REFLECTION, ENABLE_CRITIC, ENABLE_EXPLAINABILITY
from graph.edges import (
    EVIDENCE_AGGREGATOR,
    GOAL_EVALUATOR,
    OBJECTIVE_PLANNER,
    CAPABILITY_DISPATCHER,
    WORLD_MODEL,
    REFLECTION,
    CRITIC,
    EXPLAINABILITY,
    HUMAN_APPROVAL,
    ACTION_DISPATCHER,
    META_REASONER,
    MEMORY_UPDATE
)
from app.settings import ENABLE_REFLECTION, ENABLE_CRITIC, ENABLE_EXPLAINABILITY, ENABLE_HUMAN_APPROVAL
from langgraph.graph import END

logger = logging.getLogger(__name__)


def route_after_evaluator(state: TripState) -> str:
    """Decide where to go after evaluation."""
    if state.get("goal_satisfied", False):
        if ENABLE_REFLECTION:
            return REFLECTION
        elif ENABLE_CRITIC:
            return CRITIC
        elif ENABLE_EXPLAINABILITY:
            return EXPLAINABILITY
        return END

    if state.get("planner_iteration", 0) >= state.get("max_iterations", 5):
        if ENABLE_REFLECTION:
            return REFLECTION
        elif ENABLE_CRITIC:
            return CRITIC
        elif ENABLE_EXPLAINABILITY:
            return EXPLAINABILITY
        return END

    return OBJECTIVE_PLANNER


def route_after_reflection(state: TripState) -> str:
    """Route after reflection. If gaps, back to planner. Else critic/explain/end."""
    
    # If reflection added pending tool calls (gaps to fix), go back to planner
    if not state.get("planning_complete", True):
        if state.get("revision_count", 0) <= state.get("max_revisions", 2):
            return OBJECTIVE_PLANNER
            
    if ENABLE_CRITIC:
        return CRITIC
    elif ENABLE_EXPLAINABILITY:
        return EXPLAINABILITY
    return END


def route_after_critic(state: TripState) -> str:
    """Route after critic. If should_revise, back to planner. Else explain/end."""
    
    if state.get("critic_should_revise", False):
        if state.get("revision_count", 0) <= state.get("max_revisions", 2):
            return OBJECTIVE_PLANNER
            
    if ENABLE_EXPLAINABILITY:
        return EXPLAINABILITY
    elif ENABLE_HUMAN_APPROVAL:
        return HUMAN_APPROVAL
    return MEMORY_UPDATE


def route_after_explainability(state: TripState) -> str:
    """Route after explainability. If human approval enabled, go there. Else memory update."""
    if ENABLE_HUMAN_APPROVAL:
        return HUMAN_APPROVAL
    return MEMORY_UPDATE


def route_after_approval(state: TripState) -> str:
    """Route after human approval."""
    status = state.get("approval_status", "")
    if status == "rejected":
        return META_REASONER
    return ACTION_DISPATCHER


def route_after_action_dispatcher(state: TripState) -> str:
    """Route after action dispatcher. If errors, meta reasoner. Else memory update."""
    if state.get("errors"):
        return META_REASONER
    return MEMORY_UPDATE


def route_after_meta_reasoning(state: TripState) -> str:
    """Route based on meta reasoner recovery strategy."""
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
    
    return END
