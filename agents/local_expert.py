"""Local Expert specialised agent."""

from __future__ import annotations

from agents.coordinator import Agent


class LocalExpertAgent(Agent):
    """Specialises in cultural nuances, local customs, and hidden gems."""

    ROLE = "local_expert"
    SYSTEM_PROMPT = (
        "You are a Local Culture and Experiences Expert. Provide deep, authentic "
        "recommendations for food, activities, and etiquette that go beyond "
        "typical tourist traps."
    )

    def plan(self, state: dict) -> dict:
        """Stub for specialized local expertise logic."""
        return {}
