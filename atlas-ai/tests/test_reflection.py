"""Tests for the reflection node."""

from __future__ import annotations

import json
from unittest.mock import patch

from nodes.reflection import reflection


def test_reflection_identifies_gaps(sample_state_with_goal, mock_llm_response):
    mock_response = {
        "gaps": [
            {
                "category": "Visa",
                "description": "Missing visa requirements for Japan.",
                "severity": "critical",
                "suggested_action": "Check if user needs a visa for Japan."
            }
        ],
        "overall_confidence": 0.8
    }
    mock_llm = mock_llm_response(mock_response)

    with patch("nodes.reflection.get_llm", return_value=mock_llm):
        result = reflection(sample_state_with_goal)

    assert len(result["reflection_gaps"]) == 1
    assert result["reflection_gaps"][0]["severity"] == "critical"
    
    # Should create a pending tool call to fix the gap
    assert len(result["pending_tool_calls"]) == 1
    assert result["pending_tool_calls"][0]["tool"] == "address_gap"
    assert result["planning_complete"] is False


def test_reflection_ignores_low_severity_gaps(sample_state_with_goal, mock_llm_response):
    mock_response = {
        "gaps": [
            {
                "category": "Weather",
                "description": "Might rain.",
                "severity": "low",
                "suggested_action": "Pack an umbrella."
            }
        ],
        "overall_confidence": 0.9
    }
    mock_llm = mock_llm_response(mock_response)

    with patch("nodes.reflection.get_llm", return_value=mock_llm):
        result = reflection(sample_state_with_goal)

    assert len(result["reflection_gaps"]) == 1
    
    # Low severity shouldn't force planner to re-run
    assert len(result["pending_tool_calls"]) == 0
    assert result["planning_complete"] is True
