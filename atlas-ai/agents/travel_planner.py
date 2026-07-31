"""Travel Planner specialised agent."""

from __future__ import annotations

from agents.coordinator import Agent


class TravelPlannerAgent(Agent):
    """Specialises in logistics, routing, and time management."""

    ROLE = "travel_planner"
    SYSTEM_PROMPT = (
        "You are a Travel Logistics Expert. Focus on creating efficient, "
        "realistic itineraries. Pay attention to transit times, time zones, "
        "and logical geographic groupings."
    )

    def plan(self, state: dict) -> dict:
        """Stub for specialized planning logic."""
        return {}
