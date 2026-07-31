"""Tests for the goal_understanding node."""

from __future__ import annotations

import json
from unittest.mock import patch

from nodes.goal_understanding import goal_understanding
from tests.conftest import SAMPLE_PARSED_GOAL, SAMPLE_USER_INPUT


def test_goal_understanding_parses_input(sample_initial_state, mock_llm_response):
    """Test that goal_understanding extracts a structured goal from natural language."""
    mock_llm = mock_llm_response(SAMPLE_PARSED_GOAL)

    with patch("nodes.goal_understanding.get_llm", return_value=mock_llm):
        result = goal_understanding(sample_initial_state)

    assert "parsed_goal" in result
    parsed = result["parsed_goal"]
    assert parsed["destination"] == "Japan"
    assert parsed["budget"] == 150000
    assert parsed["currency"] == "INR"
    assert parsed["days"] == 5


def test_goal_understanding_handles_markdown_fences(sample_initial_state, mock_llm_response):
    """Test JSON extraction when LLM wraps response in markdown fences."""
    fenced_response = f"```json\n{json.dumps(SAMPLE_PARSED_GOAL)}\n```"
    mock_llm = mock_llm_response(fenced_response)

    with patch("nodes.goal_understanding.get_llm", return_value=mock_llm):
        result = goal_understanding(sample_initial_state)

    assert result["parsed_goal"]["destination"] == "Japan"


def test_goal_understanding_handles_invalid_json(sample_initial_state, mock_llm_response):
    """Test graceful handling of unparseable LLM output."""
    mock_llm = mock_llm_response("This is not JSON at all")

    with patch("nodes.goal_understanding.get_llm", return_value=mock_llm):
        result = goal_understanding(sample_initial_state)

    assert "parsed_goal" in result
    assert "error" in result["parsed_goal"]


def test_goal_understanding_loads_memory(sample_initial_state, mock_llm_response):
    """Test that memory_context is returned."""
    mock_llm = mock_llm_response(SAMPLE_PARSED_GOAL)

    with patch("nodes.goal_understanding.get_llm", return_value=mock_llm), \
         patch("nodes.goal_understanding.load_preferences", return_value={"preferred_airline": "IndiGo"}):
        result = goal_understanding(sample_initial_state)

    assert "memory_context" in result
    assert result["memory_context"]["preferred_airline"] == "IndiGo"
