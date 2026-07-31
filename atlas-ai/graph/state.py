"""Shared graph state definition for the AtlasAI LangGraph agent.

TripState is the single TypedDict that all nodes read from and write to.
Nodes return partial dicts with only the keys they want to update.
"""

from __future__ import annotations

from typing import TypedDict


class TripState(TypedDict, total=False):
    """Central state schema for the LangGraph travel-planning agent.

    ``total=False`` makes every key optional so nodes can return partial updates.
    The graph runner merges returned dicts into the accumulated state.
    """

    # --- User Input ---
    user_input: str

    # --- Goal Understanding ---
    parsed_goal: dict  # serialised ParsedGoal

    # --- Goal Decomposition ---
    sub_goals: list[dict]  # list of serialised SubGoal

    # --- Planner ---
    current_plan: list[dict]  # ordered planned actions
    planner_iteration: int
    planner_reasoning: list[str]  # chain-of-thought log
    planning_complete: bool  # True when planner emits empty actions

    # --- Tool dispatch ---
    tool_results: dict  # keyed by tool name → raw results
    pending_tool_calls: list[dict]  # PlannedAction dicts queued for dispatch

    # --- Evidence ---
    evidence: dict  # aggregated structured evidence by category

    # --- World Model ---
    world_facts: list[dict]  # serialised WorldFact list

    # --- Quality Assurance (Phase 2) ---
    revision_count: int
    max_revisions: int
    reflection_gaps: list[dict]
    critic_should_revise: bool
    critic_feedback: list[dict]
    reflection_notes: list[str]
    explanation: dict

    # --- Goal Evaluation ---
    goal_status: dict[str, dict]  # per sub-goal completion status
    goal_satisfied: bool
    evaluation_reasoning: str

    # --- Human Approval (Phase 3) ---
    approval_required: bool
    approval_status: str  # pending | approved | rejected
    approval_reason: str  # reason for rejection (if rejected)

    # --- Booking & Payment (Phase 3) ---
    booking_results: list[dict]
    payment_results: list[dict]

    # --- Meta-reasoning (Phase 3) ---
    failure_history: list[dict]  # log of all failures and recovery attempts
    recovery_attempts: int
    max_recovery_attempts: int  # default 3

    # --- Tool Memory (Phase 3) ---
    tool_stats: dict  # current session tool performance

    # --- Episodic Memory (Phase 3) ---
    session_summary: dict

    # --- Memory ---
    memory_context: dict  # loaded user preferences

    # --- Meta / Error Tracking ---
    errors: list[dict]
    iteration_count: int
    max_iterations: int
