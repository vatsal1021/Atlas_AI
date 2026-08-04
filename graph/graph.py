"""LangGraph StateGraph definition and compilation.

Defines the planning loop and registers instrumented nodes and routers.
"""

from __future__ import annotations

import logging
from typing import Callable, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import TripState
from graph import edges
from app.tracing import get_tracker

# Node functions
from nodes.goal_understanding import goal_understanding
from nodes.goal_decomposition import goal_decomposition
from nodes.objective_planner import objective_planner
from nodes.capability_dispatcher import capability_dispatcher
from nodes.evidence_aggregator import evidence_aggregator
from nodes.world_model import world_model
from nodes.goal_evaluator import goal_evaluator
from nodes.reflection import reflection
from nodes.critic import critic
from nodes.explainability import explainability
from nodes.human_approval import human_approval
from nodes.action_dispatcher import action_dispatcher
from nodes.meta_reasoner import meta_reasoner
from nodes.memory_update import memory_update

from graph.router import (
    route_after_evaluator,
    route_after_reflection,
    route_after_critic,
    route_after_explainability,
    route_after_approval,
    route_after_action_dispatcher,
    route_after_meta_reasoning,
)
from graph.edges import (
    GOAL_UNDERSTANDING,
    GOAL_DECOMPOSITION,
    OBJECTIVE_PLANNER,
    CAPABILITY_DISPATCHER,
    EVIDENCE_AGGREGATOR,
    WORLD_MODEL,
    GOAL_EVALUATOR,
    REFLECTION,
    CRITIC,
    EXPLAINABILITY,
    HUMAN_APPROVAL,
    ACTION_DISPATCHER,
    META_REASONER,
    MEMORY_UPDATE,
)

logger = logging.getLogger(__name__)


def _instrument_node(name: str, fn: Callable[[TripState], dict]) -> Callable[[TripState], dict]:
    """Wrap a node function to automatically log execution start, end, and state changes."""
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
    """Wrap a conditional router function to automatically log routing decisions."""
    def wrapped(state: TripState) -> str:
        target = router_fn(state)
        tracker = get_tracker()
        if tracker:
            tracker.track_routing(from_node=from_node, to_node=target)
        return target
    return wrapped


def build_graph() -> StateGraph:
    """Construct and return the (uncompiled) StateGraph."""
    builder = StateGraph(TripState)

    # --- Register instrumented nodes ---
    builder.add_node(GOAL_UNDERSTANDING, _instrument_node(GOAL_UNDERSTANDING, goal_understanding))
    builder.add_node(GOAL_DECOMPOSITION, _instrument_node(GOAL_DECOMPOSITION, goal_decomposition))
    builder.add_node(OBJECTIVE_PLANNER, _instrument_node(OBJECTIVE_PLANNER, objective_planner))
    builder.add_node(CAPABILITY_DISPATCHER, _instrument_node(CAPABILITY_DISPATCHER, capability_dispatcher))
    builder.add_node(EVIDENCE_AGGREGATOR, _instrument_node(EVIDENCE_AGGREGATOR, evidence_aggregator))
    builder.add_node(WORLD_MODEL, _instrument_node(WORLD_MODEL, world_model))
    builder.add_node(GOAL_EVALUATOR, _instrument_node(GOAL_EVALUATOR, goal_evaluator))
    
    # QA Layer (Phase 2)
    builder.add_node(REFLECTION, _instrument_node(REFLECTION, reflection))
    builder.add_node(CRITIC, _instrument_node(CRITIC, critic))
    builder.add_node(EXPLAINABILITY, _instrument_node(EXPLAINABILITY, explainability))
    
    # Phase 3 Nodes
    builder.add_node(HUMAN_APPROVAL, _instrument_node(HUMAN_APPROVAL, human_approval))
    builder.add_node(ACTION_DISPATCHER, _instrument_node(ACTION_DISPATCHER, action_dispatcher))
    builder.add_node(META_REASONER, _instrument_node(META_REASONER, meta_reasoner))
    builder.add_node(MEMORY_UPDATE, _instrument_node(MEMORY_UPDATE, memory_update))

    # --- Control Flow ---
    builder.set_entry_point(GOAL_UNDERSTANDING)
    builder.add_edge(GOAL_UNDERSTANDING, GOAL_DECOMPOSITION)
    builder.add_edge(GOAL_DECOMPOSITION, OBJECTIVE_PLANNER)

    # Planning loop
    builder.add_edge(OBJECTIVE_PLANNER, CAPABILITY_DISPATCHER)
    builder.add_edge(EVIDENCE_AGGREGATOR, WORLD_MODEL)
    builder.add_edge(WORLD_MODEL, GOAL_EVALUATOR)

    # Evaluator conditional routing
    builder.add_conditional_edges(
        GOAL_EVALUATOR,
        _instrument_router(GOAL_EVALUATOR, route_after_evaluator),
        {
            OBJECTIVE_PLANNER: OBJECTIVE_PLANNER,
            REFLECTION: REFLECTION,
            CRITIC: CRITIC,
            EXPLAINABILITY: EXPLAINABILITY,
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            MEMORY_UPDATE: MEMORY_UPDATE,
        },
    )
    
    # Reflection conditional routing
    builder.add_conditional_edges(
        REFLECTION,
        _instrument_router(REFLECTION, route_after_reflection),
        {
            OBJECTIVE_PLANNER: OBJECTIVE_PLANNER,
            CRITIC: CRITIC,
            EXPLAINABILITY: EXPLAINABILITY,
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            MEMORY_UPDATE: MEMORY_UPDATE,
        },
    )
    
    # Critic conditional routing
    builder.add_conditional_edges(
        CRITIC,
        _instrument_router(CRITIC, route_after_critic),
        {
            OBJECTIVE_PLANNER: OBJECTIVE_PLANNER,
            EXPLAINABILITY: EXPLAINABILITY,
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            MEMORY_UPDATE: MEMORY_UPDATE,
        },
    )
    
    # Explainability conditional routing
    builder.add_conditional_edges(
        EXPLAINABILITY,
        _instrument_router(EXPLAINABILITY, route_after_explainability),
        {
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            MEMORY_UPDATE: MEMORY_UPDATE,
        },
    )
    
    # Human Approval conditional routing
    builder.add_conditional_edges(
        HUMAN_APPROVAL,
        _instrument_router(HUMAN_APPROVAL, route_after_approval),
        {
            ACTION_DISPATCHER: ACTION_DISPATCHER,
            META_REASONER: META_REASONER,
        },
    )
    
    # Action Dispatcher conditional routing
    builder.add_conditional_edges(
        ACTION_DISPATCHER,
        _instrument_router(ACTION_DISPATCHER, route_after_action_dispatcher),
        {
            MEMORY_UPDATE: MEMORY_UPDATE,
            META_REASONER: META_REASONER,
        },
    )
    
    # Capability Dispatcher error edge
    def route_after_capability(state: TripState) -> str:
        if state.get("errors"):
            return META_REASONER
        return EVIDENCE_AGGREGATOR

    builder.add_conditional_edges(
        CAPABILITY_DISPATCHER,
        _instrument_router(CAPABILITY_DISPATCHER, route_after_capability),
        {
            META_REASONER: META_REASONER,
            EVIDENCE_AGGREGATOR: EVIDENCE_AGGREGATOR,
        },
    )
    
    # Meta Reasoner conditional routing
    builder.add_conditional_edges(
        META_REASONER,
        _instrument_router(META_REASONER, route_after_meta_reasoning),
        {
            CAPABILITY_DISPATCHER: CAPABILITY_DISPATCHER,
            OBJECTIVE_PLANNER: OBJECTIVE_PLANNER,
            GOAL_DECOMPOSITION: GOAL_DECOMPOSITION,
            END: END,
        },
    )
    
    # Memory update goes to END
    builder.add_edge(MEMORY_UPDATE, END)

    logger.info("Graph built with instrumented nodes and routers")
    return builder


def compile_graph():
    """Build and compile the graph, ready for invocation."""
    builder = build_graph()
    memory = MemorySaver()
    compiled = builder.compile(checkpointer=memory)
    logger.info("Graph compiled successfully with MemorySaver checkpointer")
    return compiled
