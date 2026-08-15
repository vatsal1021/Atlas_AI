"""LangGraph StateGraph definition and compilation — new architecture.

Single-pass, intent-driven, ReAct-centred graph with 13 nodes.
Preserves MemorySaver checkpointing and the full tracing/observability system.
"""

from __future__ import annotations

import logging
from typing import Callable, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

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
from graph.router import (
    route_after_intent_relevance,
    route_after_negotiation_classify,
    route_after_intent_path,
    route_after_react,
    route_after_approval,
    route_after_reflect,
    route_after_critic_gate,
)
from app.tracing import get_tracker

# Node functions
from nodes.intent_node import intent_node
from nodes.irrelevant_response import irrelevant_response
from nodes.entity_extract import entity_extract
from nodes.negotiation_classification import negotiation_classification
from nodes.negotiation_question import negotiation_question
from nodes.plan_proposal import plan_proposal
from nodes.react import react
from nodes.tool_execution import tool_execution
from nodes.human_approval import human_approval
from nodes.reflect import reflect
from nodes.critic_gate import critic_gate
from nodes.critic import critic
from nodes.relevant_response import relevant_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Instrumentation wrappers (preserves existing tracing system)
# ---------------------------------------------------------------------------

def _instrument_node(name: str, fn: Callable[[TripState], dict]) -> Callable[[TripState], dict]:
    """Wrap a node function to log execution start, end, and state changes."""
    def wrapped(state: TripState) -> dict:
        tracker = get_tracker()
        if tracker:
            tracker.track_node_start(name, state)
        try:
            update = fn(state)
            if tracker:
                tracker.track_node_end(name, state, update, status="Success")
            return update
        except Exception as e:
            if tracker:
                tracker.track_node_end(name, state, {}, status="Failed", error=str(e))
            raise
    return wrapped


def _instrument_router(from_node: str, router_fn: Callable[[TripState], str]) -> Callable[[TripState], str]:
    """Wrap a conditional router function to log routing decisions."""
    def wrapped(state: TripState) -> str:
        target = router_fn(state)
        tracker = get_tracker()
        if tracker:
            tracker.track_routing(from_node=from_node, to_node=target)
        return target
    return wrapped


# ---------------------------------------------------------------------------
# Helper: set intent_gate_mode = "path" before re-entering IntentNode
# ---------------------------------------------------------------------------

def _set_path_gate_mode(state: TripState) -> dict:
    """Thin node that flips intent_gate_mode so IntentNode acts as path gate."""
    return {"intent_gate_mode": "path"}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct and return the (uncompiled) StateGraph."""
    builder = StateGraph(TripState)

    # ── Register instrumented nodes ──────────────────────────────────────
    builder.add_node(INTENT_NODE,          _instrument_node(INTENT_NODE,          intent_node))
    builder.add_node(IRRELEVANT_RESPONSE,  _instrument_node(IRRELEVANT_RESPONSE,  irrelevant_response))
    builder.add_node(ENTITY_EXTRACT,       _instrument_node(ENTITY_EXTRACT,       entity_extract))
    builder.add_node(NEGOTIATION_CLASSIFY, _instrument_node(NEGOTIATION_CLASSIFY, negotiation_classification))
    builder.add_node(NEGOTIATION_QUESTION, _instrument_node(NEGOTIATION_QUESTION, negotiation_question))

    # Path gate mode setter — thin node, no LLM call
    PATH_GATE_SETTER = "path_gate_setter"
    builder.add_node(PATH_GATE_SETTER, _instrument_node(PATH_GATE_SETTER, _set_path_gate_mode))

    builder.add_node(PLAN_PROPOSAL,       _instrument_node(PLAN_PROPOSAL,       plan_proposal))
    builder.add_node(REACT,               _instrument_node(REACT,               react))
    builder.add_node(TOOL_EXECUTION,      _instrument_node(TOOL_EXECUTION,      tool_execution))
    builder.add_node(HUMAN_APPROVAL,      _instrument_node(HUMAN_APPROVAL,      human_approval))
    builder.add_node(REFLECT,             _instrument_node(REFLECT,             reflect))
    builder.add_node(CRITIC_GATE,         _instrument_node(CRITIC_GATE,         critic_gate))
    builder.add_node(CRITIC,              _instrument_node(CRITIC,              critic))
    builder.add_node(RELEVANT_RESPONSE,   _instrument_node(RELEVANT_RESPONSE,   relevant_response))

    # ── Entry point ──────────────────────────────────────────────────────
    builder.set_entry_point(INTENT_NODE)

    # ── IntentNode (Relevance Gate) → conditional ────────────────────────
    builder.add_conditional_edges(
        INTENT_NODE,
        _instrument_router(INTENT_NODE, _route_intent_by_mode),
        {
            ENTITY_EXTRACT:       ENTITY_EXTRACT,
            IRRELEVANT_RESPONSE:  IRRELEVANT_RESPONSE,
            PLAN_PROPOSAL:        PLAN_PROPOSAL,
            REACT:                REACT,
        },
    )

    # ── Terminal: IrrelevantResponseNode ─────────────────────────────────
    builder.add_edge(IRRELEVANT_RESPONSE, END)

    # ── EntityExtract → NegotiationClassify (fixed) ──────────────────────
    builder.add_edge(ENTITY_EXTRACT, NEGOTIATION_CLASSIFY)

    # ── NegotiationClassify → conditional ────────────────────────────────
    builder.add_conditional_edges(
        NEGOTIATION_CLASSIFY,
        _instrument_router(NEGOTIATION_CLASSIFY, route_after_negotiation_classify),
        {
            NEGOTIATION_QUESTION: NEGOTIATION_QUESTION,
            INTENT_NODE:          PATH_GATE_SETTER,   # go via setter first
        },
    )

    # ── Terminal: NegotiationQuestionNode ────────────────────────────────
    builder.add_edge(NEGOTIATION_QUESTION, END)

    # ── PathGateSetter → IntentNode (now in path mode) ───────────────────
    builder.add_edge(PATH_GATE_SETTER, INTENT_NODE)

    # ── PlanProposal → React (fixed) ─────────────────────────────────────
    builder.add_edge(PLAN_PROPOSAL, REACT)

    # ── ReactNode → conditional ──────────────────────────────────────────
    builder.add_conditional_edges(
        REACT,
        _instrument_router(REACT, route_after_react),
        {
            TOOL_EXECUTION: TOOL_EXECUTION,
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            REFLECT:        REFLECT,
        },
    )

    # ── ToolExecution → React (fixed loop back) ──────────────────────────
    builder.add_edge(TOOL_EXECUTION, REACT)

    # ── HumanApproval → conditional ──────────────────────────────────────
    builder.add_conditional_edges(
        HUMAN_APPROVAL,
        _instrument_router(HUMAN_APPROVAL, route_after_approval),
        {
            TOOL_EXECUTION: TOOL_EXECUTION,
            REACT:          REACT,
        },
    )

    # ── ReflectNode → conditional ────────────────────────────────────────
    builder.add_conditional_edges(
        REFLECT,
        _instrument_router(REFLECT, route_after_reflect),
        {
            REACT:       REACT,
            CRITIC_GATE: CRITIC_GATE,
        },
    )

    # ── CriticGate → conditional ─────────────────────────────────────────
    builder.add_conditional_edges(
        CRITIC_GATE,
        _instrument_router(CRITIC_GATE, route_after_critic_gate),
        {
            CRITIC:            CRITIC,
            RELEVANT_RESPONSE: RELEVANT_RESPONSE,
        },
    )

    # ── CriticNode → RelevantResponse (fixed) ────────────────────────────
    builder.add_edge(CRITIC, RELEVANT_RESPONSE)

    # ── Terminal: RelevantResponseNode ───────────────────────────────────
    builder.add_edge(RELEVANT_RESPONSE, END)

    logger.info("Graph built: 13 nodes, single-pass ReAct architecture")
    return builder


def _route_intent_by_mode(state: TripState) -> str:
    """Unified router for IntentNode — delegates based on current gate mode."""
    mode = state.get("intent_gate_mode", "relevance")
    if mode == "path":
        return route_after_intent_path(state)
    return route_after_intent_relevance(state)


def compile_graph():
    """Build and compile the graph with MemorySaver checkpointer."""
    builder = build_graph()
    memory = MemorySaver()
    compiled = builder.compile(checkpointer=memory)
    logger.info("Graph compiled successfully with MemorySaver checkpointer")
    return compiled
