"""Orchestration helpers for the new single-pass AtlasAI architecture."""

from __future__ import annotations

from typing import Any
from graph.state import TripState
from app.settings import DEFAULT_MAX_REACT_ITERATIONS, DEFAULT_MAX_REFLECT_ITERATIONS


def create_initial_state(
    user_input: str,
    max_react_iterations: int | None = None,
    max_reflect_iterations: int | None = None,
    existing_state: dict[str, Any] | None = None,
) -> TripState:
    """Build the TripState for a user turn, preserving prior turn state if present.

    Parameters
    ----------
    user_input : str
        The user's natural language message for this turn.
    max_react_iterations : int | None
        Override for max ReAct loop iterations.
    max_reflect_iterations : int | None
        Override for max Reflect loop iterations.
    existing_state : dict | None
        Prior checkpointed state for the thread, if any.

    Returns
    -------
    TripState
        A state dict ready to feed into the graph.
    """
    existing = existing_state or {}

    return TripState(
        # Input
        user_input=user_input,
        conversation_history=list(existing.get("conversation_history", [])),

        # Intent (reset per turn)
        intent_classification="",
        intent_gate_mode="relevance",
        path_decision="",

        # Entities & negotiation (accumulate across turns)
        extracted_entities=dict(existing.get("extracted_entities", {})),
        negotiation_status=existing.get("negotiation_status", ""),
        missing_fields=list(existing.get("missing_fields", [])),
        negotiation_reasoning="",
        negotiation_history=list(existing.get("negotiation_history", [])),

        # Planning
        planning_directive={},
        multi_agent_hint={},

        # ReAct (reset per pass)
        react_decision="",
        pending_tool_call={},
        requires_approval=False,
        tool_observations=[],
        react_reasoning_log=[],
        react_iteration=0,
        max_react_iterations=max_react_iterations or DEFAULT_MAX_REACT_ITERATIONS,

        # Tool memory (preserve across turns)
        tool_selection_memory=dict(existing.get("tool_selection_memory", {})),

        # Approval
        approval_required=False,
        approval_status="",
        approval_reason="",

        # Reflection
        reflect_decision="",
        reflect_feedback="",
        reflect_iteration=0,
        max_reflect_iterations=max_reflect_iterations or DEFAULT_MAX_REFLECT_ITERATIONS,

        # Critic
        critic_gate_decision="",
        critic_notes=[],
        critic_risk_level="",

        # Response
        final_response="",
        response_metadata={},

        # Memory & Preferences
        memory_context=dict(existing.get("memory_context", {})),
        session_summary=dict(existing.get("session_summary", {})),

        # Booking Results (accumulate confirmed bookings across turns)
        booking_results=list(existing.get("booking_results", [])),
        payment_results=list(existing.get("payment_results", [])),

        # Meta
        errors=[],
        iteration_count=existing.get("iteration_count", 0) + 1,
    )
