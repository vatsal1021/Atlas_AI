"""Budget Analyst specialised agent."""

from __future__ import annotations

from agents.coordinator import Agent


class BudgetAnalystAgent(Agent):
    """Specialises in cost estimation, constraint checking, and deals."""

    ROLE = "budget_analyst"
    SYSTEM_PROMPT = (
        "You are a Budget Analyst for travel. Ensure all plans strictly adhere "
        "to the user's financial constraints. Identify hidden costs and "
        "recommend cost-saving alternatives."
    )

    def plan(self, state: dict) -> dict:
        """Stub for specialized budgeting logic."""
        return {}
