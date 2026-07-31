"""Tests for the critic node."""

from __future__ import annotations

import json
from unittest.mock import patch

from nodes.critic import critic


def test_critic_demands_revision(sample_state_with_goal, mock_llm_response):
    mock_response = {
        "issues": [
            {
                "aspect": "Budget",
                "problem": "Hotel cost exceeds total budget.",
                "severity": "critical",
                "suggestion": "Find cheaper hotels."
            }
        ],
        "overall_rating": "poor",
        "should_revise": True
    }
    mock_llm = mock_llm_response(mock_response)

    with patch("nodes.critic.get_llm", return_value=mock_llm):
        result = critic(sample_state_with_goal)

    assert result["critic_should_revise"] is True
    assert len(result["critic_feedback"]) == 1
    assert result["planning_complete"] is False


def test_critic_approves_plan(sample_state_with_goal, mock_llm_response):
    mock_response = {
        "issues": [],
        "overall_rating": "excellent",
        "should_revise": False
    }
    mock_llm = mock_llm_response(mock_response)
    
    # Assume planning was already complete before critic
    sample_state_with_goal["planning_complete"] = True

    with patch("nodes.critic.get_llm", return_value=mock_llm):
        result = critic(sample_state_with_goal)

    assert result["critic_should_revise"] is False
    assert result["planning_complete"] is True
