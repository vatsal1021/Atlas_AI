"""Tests for the memory tool (dedicated file)."""

from __future__ import annotations

from unittest.mock import patch

from tools.memory import load_preferences, save_preferences


def test_memory_creates_file_if_missing(tmp_path):
    """Memory file should be auto-created."""
    mem_file = tmp_path / "user_memory.json"

    with patch("tools.memory._DATA_DIR", tmp_path), \
         patch("tools.memory._MEMORY_FILE", mem_file):
        loaded = load_preferences("new_user")

    assert loaded == {}
    assert mem_file.exists()


def test_memory_merges_preferences(tmp_path):
    """Saving twice should merge, not overwrite."""
    mem_file = tmp_path / "user_memory.json"
    mem_file.write_text("{}", encoding="utf-8")

    with patch("tools.memory._DATA_DIR", tmp_path), \
         patch("tools.memory._MEMORY_FILE", mem_file):
        save_preferences("u1", {"airline": "IndiGo"})
        save_preferences("u1", {"hotel_chain": "Marriott"})
        loaded = load_preferences("u1")

    assert loaded["airline"] == "IndiGo"
    assert loaded["hotel_chain"] == "Marriott"


def test_memory_isolates_users(tmp_path):
    """Different user IDs should have separate preferences."""
    mem_file = tmp_path / "user_memory.json"
    mem_file.write_text("{}", encoding="utf-8")

    with patch("tools.memory._DATA_DIR", tmp_path), \
         patch("tools.memory._MEMORY_FILE", mem_file):
        save_preferences("alice", {"pref": "A"})
        save_preferences("bob", {"pref": "B"})

        assert load_preferences("alice")["pref"] == "A"
        assert load_preferences("bob")["pref"] == "B"
