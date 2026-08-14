"""Conditional routing functions for the new AtlasAI LangGraph state graph.

Each function takes a TripState and returns the string name of the next node.
All routing is state-driven — no hardcoded workflow sequences.
"""

from __future__ import annotations

import logging

from langgraph.graph import END

from graph.state import TripState
from graph.edges import (
    INTENT_NODE,
    IRRELEVANT_RESPONSE,
    ENTITY_EXTRACT,
    NEGOTIATION_CLASSIFY,
    NEGOTIATION_QUESTION,
    PLAN_PROPOSAL,
    REACT,
    TOOL_EXECUTION,
    HUMAN_APPROVAL,
    REFLECT,
    CRITIC_GATE,
    CRITIC,
    RELEVANT_RESPONSE,
)
from app.settings import DEFAULT_MAX_REACT_ITERATIONS, DEFAULT_MAX_REFLECT_ITERATIONS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry: IntentNode (Relevance Gate)
# ---------------------------------------------------------------------------

def route_after_intent_relevance(state: TripState) -> str:
    """Route after relevance gate: relevant → entity extract, else → irrelevant response."""
    classification = state.get("intent_classification", "irrelevant")
    if classification == "relevant":
        return ENTITY_EXTRACT
    return IRRELEVANT_RESPONSE


# ---------------------------------------------------------------------------
# After EntityExtractNode → always NegotiationClassify
# (This is a fixed edge — no conditional router needed here)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# NegotiationClassificationNode
# ---------------------------------------------------------------------------

def route_after_negotiation_classify(state: TripState) -> str:
    """needs_information → question, information_complete → path gate."""
    status = state.get("negotiation_status", "information_complete")
    if status == "needs_information":
        return NEGOTIATION_QUESTION
    # Flip intent_gate_mode so IntentNode acts as path gate on next call
    return INTENT_NODE


# ---------------------------------------------------------------------------
# IntentNode (Path Gate)
# ---------------------------------------------------------------------------

def route_after_intent_path(state: TripState) -> str:
    """plan → PlanProposal, direct_execute → React."""
    decision = state.get("path_decision", "direct_execute")
    if decision == "plan":
        return PLAN_PROPOSAL
    return REACT


# ---------------------------------------------------------------------------
# ReactNode
# ---------------------------------------------------------------------------

def route_after_react(state: TripState) -> str:
    """Route based on react_decision; enforce max_react_iterations guard."""
    react_iter = state.get("react_iteration", 0)
    max_iter = state.get("max_react_iterations", DEFAULT_MAX_REACT_ITERATIONS)

    # Guard: force reflect if max iterations exceeded
    if react_iter >= max_iter:
        logger.warning("route_after_react: max_react_iterations=%d reached — forcing reflect", max_iter)
        return REFLECT

    decision = state.get("react_decision", "respond")

    if decision == "act":
        return TOOL_EXECUTION
    if decision == "critical_action":
        return HUMAN_APPROVAL
    # respond | complete → reflect
    return REFLECT


# ---------------------------------------------------------------------------
# ToolExecutionNode → always back to React
# (Fixed edge — no conditional router needed here)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# HumanApprovalNode
# ---------------------------------------------------------------------------

def route_after_approval(state: TripState) -> str:
    """approved → tool execution, rejected → back to react."""
    status = state.get("approval_status", "")
    if status == "approved":
        return TOOL_EXECUTION
    # rejected or not_needed → let react reason about alternatives
    return REACT


# ---------------------------------------------------------------------------
# ReflectNode
# ---------------------------------------------------------------------------

def route_after_reflect(state: TripState) -> str:
    """needs_more_work (within limit) → react; complete or limit exceeded → critic gate."""
    decision = state.get("reflect_decision", "complete")
    reflect_iter = state.get("reflect_iteration", 0)
    max_reflect = state.get("max_reflect_iterations", DEFAULT_MAX_REFLECT_ITERATIONS)

    if decision == "needs_more_work" and reflect_iter < max_reflect:
        return REACT

    if reflect_iter >= max_reflect:
        logger.warning("route_after_reflect: max_reflect_iterations=%d reached — forcing critic gate", max_reflect)

    return CRITIC_GATE


# ---------------------------------------------------------------------------
# CriticGate
# ---------------------------------------------------------------------------

def route_after_critic_gate(state: TripState) -> str:
    """critic_required → critic, skip → relevant response."""
    gate = state.get("critic_gate_decision", "skip")
    if gate == "critic_required":
        return CRITIC
    return RELEVANT_RESPONSE


# ---------------------------------------------------------------------------
# CriticNode → always RelevantResponse
# (Fixed edge — no conditional router needed here)
# ---------------------------------------------------------------------------
