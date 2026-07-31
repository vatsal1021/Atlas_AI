"""Tests for the explainability node."""

from __future__ import annotations

import json
from unittest.mock import patch

from nodes.explainability import explainability


def test_explainability_generates_structure(sample_state_with_goal, mock_llm_response):
    mock_response = {
        "explanation": {
            "decisions": [
                {
                    "item": "Hotel XYZ",
                    "reasoning": "Fits budget.",
                    "pros": ["Cheap"],
                    "cons": ["Far"]
                }
            ],
            "risks": [
                {
                    "risk": "Weather",
                    "mitigation": "Indoor activities planned."
                }
            ],
            "tradeoffs": ["Sacrificed location for price."],
            "alternatives": ["Considered Hotel ABC but it was expensive."]
        }
    }
    mock_llm = mock_llm_response(mock_response)

    with patch("nodes.explainability.get_llm", return_value=mock_llm):
        result = explainability(sample_state_with_goal)

    explanation = result["explanation"]
    assert "decisions" in explanation
    assert len(explanation["decisions"]) == 1
    assert "risks" in explanation
    assert "tradeoffs" in explanation
    assert "alternatives" in explanation
