"""LangGraph StateGraph definition and compilation.

Defines the Phase 1 planning loop:
  START → goal_understanding → goal_decomposition → objective_planner →
  capability_dispatcher → evidence_aggregator → world_model →
  goal_evaluator → [conditional: loop or end]
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import TripState
from graph import edges

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
    route_after_meta_reasoning
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
    MEMORY_UPDATE
)

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    """Construct and return the (uncompiled) StateGraph.

    Returns
    -------
    StateGraph
        The graph builder, ready for ``.compile()``.
    """
    builder = StateGraph(TripState)

    # --- Register nodes ---
    builder.add_node(edges.GOAL_UNDERSTANDING, goal_understanding)
    builder.add_node(edges.GOAL_DECOMPOSITION, goal_decomposition)
    builder.add_node(edges.OBJECTIVE_PLANNER, objective_planner)
    builder.add_node(edges.CAPABILITY_DISPATCHER, capability_dispatcher)
    builder.add_node(edges.EVIDENCE_AGGREGATOR, evidence_aggregator)
    builder.add_node(WORLD_MODEL, world_model)
    builder.add_node(GOAL_EVALUATOR, goal_evaluator)
    
    # QA Layer (Phase 2)
    builder.add_node(REFLECTION, reflection)
    builder.add_node(CRITIC, critic)
    builder.add_node(EXPLAINABILITY, explainability)
    
    # Phase 3 Nodes
    builder.add_node(HUMAN_APPROVAL, human_approval)
    builder.add_node(ACTION_DISPATCHER, action_dispatcher)
    builder.add_node(META_REASONER, meta_reasoner)
    builder.add_node(MEMORY_UPDATE, memory_update)

    # 3. Define the edges (Control Flow)   # Linear entry path
    builder.set_entry_point(edges.GOAL_UNDERSTANDING)
    builder.add_edge(edges.GOAL_UNDERSTANDING, edges.GOAL_DECOMPOSITION)
    builder.add_edge(edges.GOAL_DECOMPOSITION, edges.OBJECTIVE_PLANNER)

    # Planning loop: planner → dispatcher → aggregator → world_model → evaluator
    builder.add_edge(edges.OBJECTIVE_PLANNER, edges.CAPABILITY_DISPATCHER)
    # builder.add_edge(edges.CAPABILITY_DISPATCHER, edges.EVIDENCE_AGGREGATOR) <- Replaced by conditional edge
    builder.add_edge(edges.EVIDENCE_AGGREGATOR, edges.WORLD_MODEL)
    builder.add_edge(edges.WORLD_MODEL, edges.GOAL_EVALUATOR)

    # Evaluator conditional routing (Loop, Reflection, Critic, Explainability, or End)
    builder.add_conditional_edges(
        GOAL_EVALUATOR,
        route_after_evaluator,
        {
            OBJECTIVE_PLANNER: OBJECTIVE_PLANNER,
            REFLECTION: REFLECTION,
            CRITIC: CRITIC,
            EXPLAINABILITY: EXPLAINABILITY,
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            MEMORY_UPDATE: MEMORY_UPDATE
        }
    )
    
    # Reflection conditional routing
    builder.add_conditional_edges(
        REFLECTION,
        route_after_reflection,
        {
            OBJECTIVE_PLANNER: OBJECTIVE_PLANNER,
            CRITIC: CRITIC,
            EXPLAINABILITY: EXPLAINABILITY,
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            MEMORY_UPDATE: MEMORY_UPDATE
        }
    )
    
    # Critic conditional routing
    builder.add_conditional_edges(
        CRITIC,
        route_after_critic,
        {
            OBJECTIVE_PLANNER: OBJECTIVE_PLANNER,
            EXPLAINABILITY: EXPLAINABILITY,
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            MEMORY_UPDATE: MEMORY_UPDATE
        }
    )
    
    # Explainability conditional routing
    builder.add_conditional_edges(
        EXPLAINABILITY,
        route_after_explainability,
        {
            HUMAN_APPROVAL: HUMAN_APPROVAL,
            MEMORY_UPDATE: MEMORY_UPDATE
        }
    )
    
    # Human Approval conditional routing
    builder.add_conditional_edges(
        HUMAN_APPROVAL,
        route_after_approval,
        {
            ACTION_DISPATCHER: ACTION_DISPATCHER,
            META_REASONER: META_REASONER
        }
    )
    
    # Action Dispatcher conditional routing
    builder.add_conditional_edges(
        ACTION_DISPATCHER,
        route_after_action_dispatcher,
        {
            MEMORY_UPDATE: MEMORY_UPDATE,
            META_REASONER: META_REASONER
        }
    )
    
    # Error edges for tools
    def route_after_capability(state: TripState) -> str:
        if state.get("errors"):
            return META_REASONER
        return EVIDENCE_AGGREGATOR
        
    builder.add_conditional_edges(
        CAPABILITY_DISPATCHER,
        route_after_capability,
        {
            META_REASONER: META_REASONER,
            EVIDENCE_AGGREGATOR: EVIDENCE_AGGREGATOR
        }
    )
    
    # Meta Reasoner conditional routing
    builder.add_conditional_edges(
        META_REASONER,
        route_after_meta_reasoning,
        {
            CAPABILITY_DISPATCHER: CAPABILITY_DISPATCHER,
            OBJECTIVE_PLANNER: OBJECTIVE_PLANNER,
            GOAL_DECOMPOSITION: GOAL_DECOMPOSITION,
            END: END
        }
    )
    
    # Memory update goes to END
    builder.add_edge(MEMORY_UPDATE, END)

    logger.info("Graph built with %d nodes", 11)
    return builder


def compile_graph():
    """Build and compile the graph, ready for invocation.

    Returns
    -------
    CompiledGraph
        A compiled LangGraph instance with ``.invoke()`` / ``.stream()`` methods.
    """
    builder = build_graph()
    memory = MemorySaver()
    compiled = builder.compile(checkpointer=memory)
    logger.info("Graph compiled successfully with MemorySaver checkpointer")
    return compiled
