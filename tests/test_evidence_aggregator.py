"""Tests for the evidence_aggregator node."""

from __future__ import annotations

from nodes.evidence_aggregator import evidence_aggregator
from graph.planner_loop import create_initial_state


def test_aggregator_merges_flight_results():
    """Test flight results are merged into evidence under 'flights' category."""
    state = create_initial_state("test", max_iterations=3)
    state["tool_results"] = {
        "search_flights": [
            {"airline": "Air India", "price": 45000, "flight_number": "AI101"},
            {"airline": "IndiGo", "price": 38000, "flight_number": "6E201"},
        ]
    }

    result = evidence_aggregator(state)

    assert "evidence" in result
    assert "flights" in result["evidence"]
    assert len(result["evidence"]["flights"]["items"]) == 2


def test_aggregator_merges_multiple_tool_results():
    """Test multiple tool results are merged into separate categories."""
    state = create_initial_state("test", max_iterations=3)
    state["tool_results"] = {
        "search_flights": [{"airline": "Air India", "price": 45000, "flight_number": "AI101"}],
        "search_hotels": [{"name": "Hotel A", "price_per_night": 3000}],
        "get_weather": [{"date": "2026-09-01", "condition": "Sunny"}],
    }

    result = evidence_aggregator(state)

    assert "flights" in result["evidence"]
    assert "hotels" in result["evidence"]
    assert "weather" in result["evidence"]


def test_aggregator_deduplicates():
    """Test that duplicate items are not added twice."""
    state = create_initial_state("test", max_iterations=3)
    state["evidence"] = {
        "flights": {
            "items": [{"airline": "Air India", "flight_number": "AI101"}],
            "last_updated": "2026-01-01",
            "source_tool": "search_flights",
        }
    }
    state["tool_results"] = {
        "search_flights": [
            {"airline": "Air India", "flight_number": "AI101"},  # duplicate
            {"airline": "IndiGo", "flight_number": "6E201"},     # new
        ]
    }

    result = evidence_aggregator(state)

    # Should have 2 items (1 existing + 1 new), not 3
    assert len(result["evidence"]["flights"]["items"]) == 2


def test_aggregator_handles_empty_results():
    """Test graceful handling of empty tool results."""
    state = create_initial_state("test", max_iterations=3)
    state["tool_results"] = {}

    result = evidence_aggregator(state)

    assert "evidence" in result
    assert isinstance(result["evidence"], dict)
