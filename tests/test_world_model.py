"""Tests for the world_model node."""

from __future__ import annotations

import json
from unittest.mock import patch

from nodes.world_model import world_model
from tests.conftest import SAMPLE_WORLD_FACTS


def test_world_model_produces_facts(sample_state_with_evidence, mock_llm_response):
    """Test that world_model produces structured facts from evidence."""
    mock_llm = mock_llm_response(SAMPLE_WORLD_FACTS)

    with patch("nodes.world_model.get_llm", return_value=mock_llm):
        result = world_model(sample_state_with_evidence)

    assert "world_facts" in result
    assert len(result["world_facts"]) >= 1
    for fact in result["world_facts"]:
        assert "id" in fact
        assert "statement" in fact
        assert "confidence" in fact


def test_world_model_accumulates_facts(sample_state_with_evidence, mock_llm_response):
    """Test that new facts are appended, not replacing existing ones."""
    # Prepopulate with an existing fact
    sample_state_with_evidence["world_facts"] = [
        {"id": "wf-0", "category": "general", "statement": "Existing fact", "confidence": 1.0}
    ]
    new_facts = [{"id": "wf-1", "category": "flights", "statement": "New fact", "confidence": 0.9}]
    mock_llm = mock_llm_response(new_facts)

    with patch("nodes.world_model.get_llm", return_value=mock_llm):
        result = world_model(sample_state_with_evidence)

    assert len(result["world_facts"]) == 2
    ids = {f["id"] for f in result["world_facts"]}
    assert "wf-0" in ids
    assert "wf-1" in ids


def test_world_model_deduplicates_by_id(sample_state_with_evidence, mock_llm_response):
    """Test that facts with duplicate IDs are not added."""
    sample_state_with_evidence["world_facts"] = [
        {"id": "wf-1", "category": "flights", "statement": "Existing", "confidence": 0.9}
    ]
    duplicate_facts = [
        {"id": "wf-1", "category": "flights", "statement": "Duplicate", "confidence": 0.9}
    ]
    mock_llm = mock_llm_response(duplicate_facts)

    with patch("nodes.world_model.get_llm", return_value=mock_llm):
        result = world_model(sample_state_with_evidence)

    assert len(result["world_facts"]) == 1


def test_world_model_handles_no_evidence():
    """Test that world_model returns existing facts when no evidence."""
    from graph.planner_loop import create_initial_state
    state = create_initial_state("test", max_iterations=3)
    state["world_facts"] = [{"id": "wf-1", "statement": "existing"}]

    result = world_model(state)

    assert result["world_facts"] == [{"id": "wf-1", "statement": "existing"}]
