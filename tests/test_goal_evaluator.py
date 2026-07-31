"""Tests for the goal_evaluator node."""

from __future__ import annotations

import json
from unittest.mock import patch

from nodes.goal_evaluator import goal_evaluator


def test_evaluator_marks_goals_satisfied(sample_state_with_evidence, mock_llm_response):
    """Test that evaluator correctly marks goals as satisfied."""
    eval_response = {
        "sub_goal_statuses": {
            "sg-1": {"satisfied": True, "reasoning": "Flight options found."},
            "sg-2": {"satisfied": True, "reasoning": "Hotel options found."},
            "sg-3": {"satisfied": False, "reasoning": "No activity info yet."},
            "sg-4": {"satisfied": False, "reasoning": "No restaurant info."},
            "sg-5": {"satisfied": False, "reasoning": "Budget not verified."},
        },
        "all_satisfied": False,
        "summary": "Partial progress — flights and hotels found but activities and dining pending.",
    }
    mock_llm = mock_llm_response(eval_response)

    with patch("nodes.goal_evaluator.get_llm", return_value=mock_llm):
        result = goal_evaluator(sample_state_with_evidence)

    assert result["goal_satisfied"] is False
    assert "sg-1" in result["goal_status"]
    assert result["goal_status"]["sg-1"]["satisfied"] is True

    # Check sub-goal status updates
    sg_statuses = {sg["id"]: sg["status"] for sg in result["sub_goals"]}
    assert sg_statuses["sg-1"] == "completed"
    assert sg_statuses["sg-3"] == "in_progress"


def test_evaluator_all_satisfied(sample_state_with_evidence, mock_llm_response):
    """Test all_satisfied=True correctly propagates."""
    eval_response = {
        "sub_goal_statuses": {
            "sg-1": {"satisfied": True, "reasoning": "Done."},
            "sg-2": {"satisfied": True, "reasoning": "Done."},
            "sg-3": {"satisfied": True, "reasoning": "Done."},
            "sg-4": {"satisfied": True, "reasoning": "Done."},
            "sg-5": {"satisfied": True, "reasoning": "Done."},
        },
        "all_satisfied": True,
        "summary": "All sub-goals satisfied!",
    }
    mock_llm = mock_llm_response(eval_response)

    with patch("nodes.goal_evaluator.get_llm", return_value=mock_llm):
        result = goal_evaluator(sample_state_with_evidence)

    assert result["goal_satisfied"] is True
    assert "All sub-goals" in result["evaluation_reasoning"]


def test_evaluator_handles_malformed_response(sample_state_with_evidence, mock_llm_response):
    """Test graceful handling of unparseable evaluator output."""
    mock_llm = mock_llm_response("not json")

    with patch("nodes.goal_evaluator.get_llm", return_value=mock_llm):
        result = goal_evaluator(sample_state_with_evidence)

    assert result["goal_satisfied"] is False
    assert "goal_status" in result
