"""Orchestration helpers for the new single-pass AtlasAI architecture."""

from __future__ import annotations

from graph.state import TripState
from app.settings import DEFAULT_MAX_REACT_ITERATIONS, DEFAULT_MAX_REFLECT_ITERATIONS


def create_initial_state(
    user_input: str,
    max_react_iterations: int | None = None,
    max_reflect_iterations: int | None = None,
) -> TripState:
    """Build the initial TripState for a new user message.

    Parameters
    ----------
    user_input : str
        The user's natural language message.
    max_react_iterations : int | None
        Override for max ReAct loop iterations.
    max_reflect_iterations : int | None
        Override for max Reflect loop iterations.

    Returns
    -------
    TripState
        A fully initialised state dict ready to feed into the graph.
    """
    return TripState(
        # Input
        user_input=user_input,
        conversation_history=[],

        # Intent (will be set by IntentNode)
        intent_classification="",
        intent_gate_mode="relevance",
        path_decision="",

        # Entities & negotiation
        extracted_entities={},
        negotiation_status="",
        missing_fields=[],
        negotiation_reasoning="",
        negotiation_history=[],

        # Planning
        planning_directive={},
        multi_agent_hint={},

        # ReAct
        react_decision="",
        pending_tool_call={},
        requires_approval=False,
        tool_observations=[],
        react_reasoning_log=[],
        react_iteration=0,
        max_react_iterations=max_react_iterations or DEFAULT_MAX_REACT_ITERATIONS,

        # Tool memory
        tool_selection_memory={},

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

        # Memory
        memory_context={},
        session_summary={},

        # Booking
        booking_results=[],
        payment_results=[],

        # Meta
        errors=[],
        iteration_count=0,
    )
