"""Tests for the objective_planner node."""

from __future__ import annotations

import json
from unittest.mock import patch

from nodes.objective_planner import objective_planner
from tests.conftest import SAMPLE_PLANNER_ACTIONS


def test_planner_produces_actions(sample_state_with_subgoals, mock_llm_response):
    """Test that planner outputs a list of tool call actions."""
    mock_llm = mock_llm_response(SAMPLE_PLANNER_ACTIONS)

    with patch("nodes.objective_planner.get_llm", return_value=mock_llm):
        result = objective_planner(sample_state_with_subgoals)

    assert "pending_tool_calls" in result
    assert len(result["pending_tool_calls"]) >= 1
    assert result["planner_iteration"] == 1
    assert result["planning_complete"] is False


def test_planner_increments_iteration(sample_state_with_subgoals, mock_llm_response):
    """Test that planner correctly increments the iteration counter."""
    sample_state_with_subgoals["planner_iteration"] = 3
    mock_llm = mock_llm_response(SAMPLE_PLANNER_ACTIONS)

    with patch("nodes.objective_planner.get_llm", return_value=mock_llm):
        result = objective_planner(sample_state_with_subgoals)

    assert result["planner_iteration"] == 4


def test_planner_signals_completion_on_empty_actions(sample_state_with_subgoals, mock_llm_response):
    """Test that empty actions list sets planning_complete to True."""
    mock_llm = mock_llm_response([])

    with patch("nodes.objective_planner.get_llm", return_value=mock_llm):
        result = objective_planner(sample_state_with_subgoals)

    assert result["planning_complete"] is True
    assert result["pending_tool_calls"] == []


def test_planner_appends_reasoning(sample_state_with_subgoals, mock_llm_response):
    """Test that reasoning log accumulates."""
    sample_state_with_subgoals["planner_reasoning"] = ["Iteration 1: Planned 2 action(s)."]
    mock_llm = mock_llm_response(SAMPLE_PLANNER_ACTIONS)

    with patch("nodes.objective_planner.get_llm", return_value=mock_llm):
        result = objective_planner(sample_state_with_subgoals)

    assert len(result["planner_reasoning"]) == 2
