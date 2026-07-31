"""Tests for tool stubs (travel_research, weather, memory, constraint_checker)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.travel_research import search_flights, search_hotels
from tools.weather import get_weather
from tools.memory import load_preferences, save_preferences
from tools.constraint_checker import check_constraints


class TestSearchFlights:
    """Tests for the search_flights tool."""

    def test_returns_list(self):
        results = search_flights("Delhi", "Tokyo", "2026-09-01", 1)
        assert isinstance(results, list)
        assert len(results) >= 3

    def test_result_has_required_fields(self):
        results = search_flights("Mumbai", "London", "2026-10-15", 2)
        for flight in results:
            assert "airline" in flight
            assert "flight_number" in flight
            assert "price" in flight
            assert "origin" in flight
            assert "destination" in flight

    def test_deterministic_with_same_seed(self):
        """Same inputs should produce same outputs (seeded RNG)."""
        r1 = search_flights("Delhi", "Tokyo", "2026-09-01", 1)
        r2 = search_flights("Delhi", "Tokyo", "2026-09-01", 1)
        assert r1 == r2

    def test_different_inputs_different_results(self):
        r1 = search_flights("Delhi", "Tokyo", "2026-09-01", 1)
        r2 = search_flights("Delhi", "Paris", "2026-09-01", 1)
        assert r1 != r2


class TestSearchHotels:
    """Tests for the search_hotels tool."""

    def test_returns_list(self):
        results = search_hotels("Tokyo", "2026-09-01", "2026-09-06", 1)
        assert isinstance(results, list)
        assert len(results) >= 4

    def test_result_has_required_fields(self):
        results = search_hotels("Paris", "2026-10-01", "2026-10-05", 2)
        for hotel in results:
            assert "name" in hotel
            assert "price_per_night" in hotel
            assert "rating" in hotel


class TestGetWeather:
    """Tests for the get_weather tool."""

    def test_returns_list(self):
        results = get_weather("Tokyo", "2026-09-01", "2026-09-05")
        assert isinstance(results, list)
        assert len(results) == 5

    def test_result_has_required_fields(self):
        results = get_weather("London", "2026-10-01", "2026-10-03")
        for day in results:
            assert "date" in day
            assert "temperature_high" in day
            assert "condition" in day
            assert "rain_probability" in day


class TestMemory:
    """Tests for the memory tool."""

    def test_save_and_load(self, tmp_path):
        """Test round-trip save and load of preferences."""
        mem_file = tmp_path / "user_memory.json"
        mem_file.write_text("{}", encoding="utf-8")

        with patch("tools.memory._DATA_DIR", tmp_path), \
             patch("tools.memory._MEMORY_FILE", mem_file):
            save_preferences("test_user", {"preferred_airline": "IndiGo"})
            loaded = load_preferences("test_user")

        assert loaded["preferred_airline"] == "IndiGo"

    def test_load_nonexistent_user(self, tmp_path):
        """Loading a non-existent user should return empty dict."""
        mem_file = tmp_path / "user_memory.json"
        mem_file.write_text("{}", encoding="utf-8")

        with patch("tools.memory._DATA_DIR", tmp_path), \
             patch("tools.memory._MEMORY_FILE", mem_file):
            loaded = load_preferences("nonexistent")

        assert loaded == {}


class TestConstraintChecker:
    """Tests for the constraint_checker tool."""

    def test_no_violations_within_budget(self):
        plan = {"total_cost": 100000}
        result = check_constraints(plan, budget=150000)
        assert result == []

    def test_budget_violation(self):
        plan = {"total_cost": 200000}
        result = check_constraints(plan, budget=150000)
        assert len(result) == 1
        assert result[0]["severity"] == "error"

    def test_date_violation(self):
        plan = {"total_cost": 100000, "start_date": "2026-09-10", "end_date": "2026-09-01"}
        result = check_constraints(plan, budget=150000)
        assert any(v["constraint"] == "start_date <= end_date" for v in result)
