"""Orchestration helpers for the plan-execute-evaluate loop."""

from __future__ import annotations

from graph.state import TripState
from app.settings import DEFAULT_MAX_ITERATIONS, DEFAULT_MAX_RECOVERY_ATTEMPTS


def create_initial_state(
    user_input: str,
    max_iterations: int | None = None,
) -> TripState:
    """Build the initial TripState for a new planning session.

    Parameters
    ----------
    user_input : str
        The user's natural language travel request.
    max_iterations : int | None
        Override for max planner iterations.

    Returns
    -------
    TripState
        A fully initialised state dict ready to feed into the graph.
    """
    return TripState(
        user_input=user_input,
        parsed_goal={},
        sub_goals=[],
        current_plan=[],
        planner_iteration=0,
        planner_reasoning=[],
        revision_count=0,
        max_revisions=2,
        reflection_gaps=[],
        critic_should_revise=False,
        planning_complete=False,
        tool_results={},
        pending_tool_calls=[],
        evidence={},
        world_facts=[],
        goal_status={},
        goal_satisfied=False,
        evaluation_reasoning="",
        reflection_notes=[],
        critic_feedback=[],
        explanation={},
        approval_required=False,
        approval_status="",
        approval_reason="",
        memory_context={},
        errors=[],
        iteration_count=0,
        max_iterations=max_iterations or DEFAULT_MAX_ITERATIONS,
        # Phase 3
        booking_results=[],
        payment_results=[],
        failure_history=[],
        recovery_attempts=0,
        max_recovery_attempts=DEFAULT_MAX_RECOVERY_ATTEMPTS,
        tool_stats={},
        session_summary={},
    )
