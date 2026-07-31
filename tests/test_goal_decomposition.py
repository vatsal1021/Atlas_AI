"""Tests for the goal_decomposition node."""

from __future__ import annotations

import json
from unittest.mock import patch

from nodes.goal_decomposition import goal_decomposition
from tests.conftest import SAMPLE_SUB_GOALS


def test_goal_decomposition_produces_sub_goals(sample_state_with_goal, mock_llm_response):
    """Test that goal_decomposition produces a list of sub-goals."""
    mock_llm = mock_llm_response(SAMPLE_SUB_GOALS)

    with patch("nodes.goal_decomposition.get_llm", return_value=mock_llm):
        result = goal_decomposition(sample_state_with_goal)

    assert "sub_goals" in result
    assert len(result["sub_goals"]) >= 3
    assert all("id" in sg for sg in result["sub_goals"])
    assert all("category" in sg for sg in result["sub_goals"])


def test_goal_decomposition_sub_goals_have_required_fields(sample_state_with_goal, mock_llm_response):
    """Verify sub-goals have all required fields."""
    mock_llm = mock_llm_response(SAMPLE_SUB_GOALS)

    with patch("nodes.goal_decomposition.get_llm", return_value=mock_llm):
        result = goal_decomposition(sample_state_with_goal)

    for sg in result["sub_goals"]:
        assert "id" in sg
        assert "category" in sg
        assert "description" in sg
        assert "status" in sg
        assert sg["status"] == "pending"


def test_goal_decomposition_handles_empty_response(sample_state_with_goal, mock_llm_response):
    """Test graceful handling when LLM returns no sub-goals."""
    mock_llm = mock_llm_response("not valid json")

    with patch("nodes.goal_decomposition.get_llm", return_value=mock_llm):
        result = goal_decomposition(sample_state_with_goal)

    assert "sub_goals" in result
    assert isinstance(result["sub_goals"], list)
