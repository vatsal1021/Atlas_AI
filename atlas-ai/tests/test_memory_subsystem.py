"""Tests for the memory subsystem."""

import os
import json
import pytest

from memory.tool_memory import record_tool_use, get_tool_stats
from memory.episodic_memory import store_episode, recall_similar_trips
from memory.user_memory import store_preference, retrieve_preferences

# Just test tool_memory properly as it doesn't require ChromaDB mocking
def test_tool_memory():
    """Test recording and retrieving tool stats."""
    import memory.tool_memory
    
    # Reset stats for testing
    memory.tool_memory._STATS = {}
    
    # Record success
    record_tool_use("search_flights", True, 150)
    record_tool_use("search_flights", True, 200)
    
    # Record failure
    record_tool_use("search_flights", False, 50, "Network Error")
    
    stats = get_tool_stats("search_flights")
    assert stats["invocations"] == 3
    assert stats["success_rate"] == 2.0 / 3.0
    assert stats["failures"] == 1
    assert stats["avg_latency_ms"] == (150 + 200 + 50) / 3

def test_user_memory_fallback():
    """Test user memory graceful fallback when ChromaDB is not installed or mocked."""
    # Since we can't easily run ChromaDB in standard pytest without complex mocking,
    # we just verify it doesn't crash on standard usage.
    store_preference("user_1", "food", "Likes spicy food")
    prefs = retrieve_preferences("user_1", "spicy food")
    # Will be empty due to mock warning or actual insert if Chroma works locally
    assert isinstance(prefs, list)

def test_episodic_memory_fallback():
    """Test episodic memory graceful fallback."""
    episode = {
        "user_id": "user_1",
        "destination": "Tokyo",
        "plan_summary": "Great trip.",
        "satisfaction_score": 1.0,
    }
    store_episode(episode)
    trips = recall_similar_trips("Tokyo")
    assert isinstance(trips, list)
