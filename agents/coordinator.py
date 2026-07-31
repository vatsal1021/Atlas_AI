"""Agent abstractions for the multi-agent skeleton.

Defines the base Agent interface and the CoordinatorAgent which manages
delegation. Currently delegates solely to the objective_planner.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.state import TripState
from nodes.objective_planner import objective_planner

logger = logging.getLogger(__name__)


class Agent:
    """Base class for all specialised agents."""

    ROLE = "base_agent"
    SYSTEM_PROMPT = "You are a helpful AI assistant."

    def plan(self, state: TripState) -> dict[str, Any]:
        """Generate a plan of action."""
        raise NotImplementedError

    def execute(self, state: TripState) -> dict[str, Any]:
        """Execute the plan."""
        raise NotImplementedError

    def evaluate(self, state: TripState) -> dict[str, Any]:
        """Evaluate the results of execution."""
        raise NotImplementedError


class CoordinatorAgent(Agent):
    """Orchestrates work among specialised sub-agents.

    In Phase 3, this is an architectural skeleton that simply delegates
    the core planning loop to the existing objective_planner node.
    """

    ROLE = "coordinator"
    SYSTEM_PROMPT = (
        "You are the Lead Travel Coordinator. Your job is to delegate tasks "
        "to specialised agents (Travel Planner, Budget Analyst, Local Expert, "
        "Booking Specialist) and assemble their outputs into a cohesive plan."
    )

    def plan(self, state: TripState) -> dict[str, Any]:
        """Delegate to the appropriate specialised agent.

        For now, delegates everything to the objective_planner node to maintain
        the existing system behaviour while preparing for the multi-agent graph.
        """
        logger.info("CoordinatorAgent: Delegating to objective_planner.")
        
        # In a full multi-agent setup, this would inspect state.sub_goals
        # and route to the respective sub-agent based on category.
        
        return objective_planner(state)

    def execute(self, state: TripState) -> dict[str, Any]:
        """Execute is handled by the graph's capability_dispatcher."""
        return {}

    def evaluate(self, state: TripState) -> dict[str, Any]:
        """Evaluate is handled by the graph's goal_evaluator."""
        return {}
