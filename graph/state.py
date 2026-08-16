"""Shared graph state definition for the AtlasAI LangGraph agent.

TripState is the single TypedDict that all nodes read from and write to.
Nodes return partial dicts with only the keys they want to update.

New architecture: single-pass, intent-driven, ReAct-centred graph.
"""

from __future__ import annotations

from typing import TypedDict


class TripState(TypedDict, total=False):
    """Central state schema for the LangGraph travel-planning agent.

    ``total=False`` makes every key optional so nodes can return partial updates.
    The graph runner merges returned dicts into the accumulated state.
    """

    # ── Input ──────────────────────────────────────────────────────────
    user_input: str                      # current user message
    conversation_history: list[dict]     # [{role, content}] across all turns
    thread_id: str                       # session identifier for persistence

    # ── Intent ─────────────────────────────────────────────────────────
    intent_classification: str           # relevant | irrelevant | empty
    intent_gate_mode: str                # relevance | path
    path_decision: str                   # plan | direct_execute

    # ── Entity Extraction ───────────────────────────────────────────────
    extracted_entities: dict             # destination, budget, dates, travelers, etc.

    # ── Negotiation ─────────────────────────────────────────────────────
    negotiation_status: str              # needs_information | information_complete
    missing_fields: list[str]            # fields the agent still needs
    negotiation_reasoning: str           # why information is incomplete
    negotiation_history: list[dict]      # [{question, answer}] per turn

    # ── Planning Directive ──────────────────────────────────────────────
    planning_directive: dict             # objective, constraints, decisions, success_criteria
    multi_agent_hint: dict               # future multi-agent extension point

    # ── ReAct Loop ──────────────────────────────────────────────────────
    react_decision: str                  # act | critical_action | respond | complete
    pending_tool_call: dict              # {tool, arguments, reasoning}
    requires_approval: bool              # True → triggers HumanApprovalNode
    tool_observations: list[dict]        # [{tool, args, result, status, timestamp}]
    react_reasoning_log: list[str]       # chain-of-thought entries per ReAct step
    react_iteration: int                 # current ReAct step counter
    max_react_iterations: int            # runaway-loop guard (default: 8)

    # ── Tool Selection Memory ───────────────────────────────────────────
    tool_selection_memory: dict          # {tool_name: {success_rate, avg_latency, failures}}

    # ── Human Approval ──────────────────────────────────────────────────
    approval_required: bool
    approval_status: str                 # pending | approved | rejected | not_needed
    approval_reason: str                 # free-text rejection reason

    # ── Reflection ──────────────────────────────────────────────────────
    reflect_decision: str                # needs_more_work | complete
    reflect_feedback: str                # guidance written back to ReactNode
    reflect_iteration: int               # how many times reflect has looped back
    max_reflect_iterations: int          # loop guard (default: 3)

    # ── Critic ──────────────────────────────────────────────────────────
    critic_gate_decision: str            # skip | critic_required
    critic_notes: list[str]             # issues / risks found by CriticNode
    critic_risk_level: str               # low | medium | high

    # ── Response ────────────────────────────────────────────────────────
    final_response: str                  # the text shown to the user in chat
    response_metadata: dict              # reasoning, recommendations, risks, warnings

    # ── Memory / Persistence ────────────────────────────────────────────
    memory_context: dict                 # user preferences (loaded from long-term memory)
    session_summary: dict                # summary of this session

    # ── Booking Results ─────────────────────────────────────────────────
    booking_results: list[dict]          # confirmed bookings this session
    payment_results: list[dict]          # confirmed payments this session

    # ── Booking Readiness & Capability ──────────────────────────────────
    booking_flow_active: bool            # True while user is in active train/flight/hotel booking flow
    selected_booking: dict               # Specific train/flight/hotel option selected by user
    booking_type: str                    # train | flight | hotel
    booking_details: dict                # selected train/flight/hotel details
    booking_requirements: dict           # validator output dict
    missing_booking_fields: list[str]    # missing required fields (e.g. ["passenger.age"])
    booking_requirements_complete: bool  # True when all required fields present
    booking_capability_available: bool   # True when authenticated API provider configured
    booking_capability_reason: str       # explanation if capability is unavailable
    booking_ready: bool                  # booking_requirements_complete AND booking_capability_available
    passenger_info: list[dict]           # accumulated passenger details across turns
    guest_info: dict                     # accumulated guest details across turns

    # ── Error / Meta ────────────────────────────────────────────────────
    errors: list[dict]                   # error log
    iteration_count: int                 # total graph node executions
