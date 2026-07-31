"""Tests for the meta-reasoner node."""

from unittest.mock import patch
import pytest

from graph.state import TripState
from nodes.meta_reasoner import meta_reasoner


@pytest.fixture
def mock_meta_reasoner_llm(mock_llm_response):
    """Mock the LLM response for the meta reasoner."""
    response_json = {
        "diagnosis": "The flight booking tool failed due to a network timeout.",
        "failed_component": "book_flight",
        "recovery_strategy": "retry",
        "actions": [
            {
                "tool": "book_flight",
                "parameters": {"flight_id": "123"},
                "reasoning": "Transient error, retrying should work."
            }
        ],
        "reasoning": "Network timeouts are usually transient."
    }
    return mock_llm_response(response_json)


def test_meta_reasoner_retry(sample_initial_state: TripState, mock_meta_reasoner_llm):
    """Test that meta-reasoner correctly parses a retry strategy."""
    state = sample_initial_state
    state["errors"] = [{"tool": "book_flight", "error": "Network timeout"}]
    
    with patch("nodes.meta_reasoner.get_llm", return_value=mock_meta_reasoner_llm):
        result = meta_reasoner(state)
        
        assert "failure_history" in result
        assert len(result["failure_history"]) == 1
        assert result["failure_history"][0]["strategy"] == "retry"
        assert result["recovery_attempts"] == 1
        assert len(result["pending_tool_calls"]) == 1
        assert result["pending_tool_calls"][0]["tool"] == "book_flight"


def test_meta_reasoner_escalate_max_attempts(sample_initial_state: TripState):
    """Test that meta-reasoner escalates if max recovery attempts are reached."""
    state = sample_initial_state
    state["recovery_attempts"] = 3
    state["max_recovery_attempts"] = 3
    state["errors"] = [{"tool": "book_flight", "error": "Persistent error"}]
    
    # We shouldn't even call the LLM here
    result = meta_reasoner(state)
    
    assert result["failure_history"][0]["strategy"] == "escalate"
    assert "explanation" in result
    assert result["explanation"]["escalation"] is True
