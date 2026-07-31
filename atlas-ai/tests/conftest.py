"""Shared test fixtures for AtlasAI."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from graph.state import TripState
from graph.planner_loop import create_initial_state


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_USER_INPUT = "Plan me a 5-day Japan trip with a budget of 1.5 lakh INR"

SAMPLE_PARSED_GOAL = {
    "destination": "Japan",
    "budget": 150000,
    "currency": "INR",
    "days": 5,
    "start_date": "2026-09-01",
    "end_date": "2026-09-05",
    "travelers": 1,
    "preferences": ["temples", "local cuisine", "cherry blossoms"],
    "constraints": ["vegetarian food available"],
    "inferred_fields": ["start_date", "end_date"],
}

SAMPLE_SUB_GOALS = [
    {
        "id": "sg-1",
        "category": "travel",
        "description": "Find round-trip flights from India to Japan",
        "dependencies": [],
        "status": "pending",
        "priority": 1,
    },
    {
        "id": "sg-2",
        "category": "accommodation",
        "description": "Find hotels in Tokyo for 5 nights",
        "dependencies": ["sg-1"],
        "status": "pending",
        "priority": 1,
    },
    {
        "id": "sg-3",
        "category": "activities",
        "description": "Research temples and cultural activities in Japan",
        "dependencies": [],
        "status": "pending",
        "priority": 2,
    },
    {
        "id": "sg-4",
        "category": "food",
        "description": "Find vegetarian-friendly restaurants in Tokyo",
        "dependencies": [],
        "status": "pending",
        "priority": 3,
    },
    {
        "id": "sg-5",
        "category": "budget",
        "description": "Ensure total trip cost stays within 1.5 lakh INR",
        "dependencies": ["sg-1", "sg-2"],
        "status": "pending",
        "priority": 1,
    },
]

SAMPLE_PLANNER_ACTIONS = [
    {
        "tool": "search_flights",
        "parameters": {
            "origin": "Delhi",
            "destination": "Tokyo",
            "date": "2026-09-01",
            "passengers": 1,
        },
        "reasoning": "Need to find flight options to estimate travel costs.",
        "sub_goal_id": "sg-1",
    },
    {
        "tool": "search_hotels",
        "parameters": {
            "destination": "Tokyo",
            "checkin": "2026-09-01",
            "checkout": "2026-09-06",
            "guests": 1,
        },
        "reasoning": "Need accommodation options for budget estimation.",
        "sub_goal_id": "sg-2",
    },
]

SAMPLE_WORLD_FACTS = [
    {
        "id": "wf-1",
        "category": "flights",
        "statement": "Cheapest round-trip flight to Tokyo is ₹45,000 (Air India, 1 stop)",
        "confidence": 0.9,
        "source_tool": "search_flights",
        "implications": ["Consumes 30% of budget"],
    },
    {
        "id": "wf-2",
        "category": "hotels",
        "statement": "Budget hotels in Tokyo available from ₹3,000/night",
        "confidence": 0.85,
        "source_tool": "search_hotels",
        "implications": ["5 nights = ₹15,000 minimum"],
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_initial_state() -> TripState:
    """Return a fresh initial TripState."""
    return create_initial_state(SAMPLE_USER_INPUT, max_iterations=3)


@pytest.fixture
def sample_state_with_goal() -> TripState:
    """Return a state after goal_understanding has run."""
    state = create_initial_state(SAMPLE_USER_INPUT, max_iterations=3)
    state["parsed_goal"] = SAMPLE_PARSED_GOAL
    state["memory_context"] = {}
    return state


@pytest.fixture
def sample_state_with_subgoals() -> TripState:
    """Return a state after goal_decomposition has run."""
    state = create_initial_state(SAMPLE_USER_INPUT, max_iterations=3)
    state["parsed_goal"] = SAMPLE_PARSED_GOAL
    state["sub_goals"] = SAMPLE_SUB_GOALS
    return state


@pytest.fixture
def sample_state_with_evidence() -> TripState:
    """Return a state with evidence and world facts populated."""
    state = create_initial_state(SAMPLE_USER_INPUT, max_iterations=3)
    state["parsed_goal"] = SAMPLE_PARSED_GOAL
    state["sub_goals"] = SAMPLE_SUB_GOALS
    state["world_facts"] = SAMPLE_WORLD_FACTS
    state["evidence"] = {
        "flights": {"items": [{"airline": "Air India", "price": 45000}], "last_updated": "2026-09-01"},
        "hotels": {"items": [{"name": "Budget Inn Tokyo", "price_per_night": 3000}], "last_updated": "2026-09-01"},
    }
    return state


@pytest.fixture
def mock_llm_response():
    """Factory fixture that returns a mock LLM with a given response."""
    def _make_mock(content: str | dict | list):
        if not isinstance(content, str):
            content = json.dumps(content)
        mock_response = MagicMock()
        mock_response.content = content
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        return mock_llm
    return _make_mock
