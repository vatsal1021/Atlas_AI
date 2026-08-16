"""Tests for the observability & tool-specific runtime JSON system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from app.tracing import (
    ExecutionTracker,
    RuntimeTracer,
    get_tracker,
    set_tracker,
    start_execution_tracker,
    _pretty,
    _summarize_tool_output,
    _summarize_update,
)


def _make_tracker(tmp_path: Path, run_id: str = "testrun1") -> ExecutionTracker:
    """Build an ExecutionTracker that writes to tmp_path."""
    import time
    tracker = ExecutionTracker.__new__(ExecutionTracker)
    tracker.run_id = run_id
    tracker.user_input = "Plan a trip to Goa"
    tracker.base_dir = tmp_path
    tracker.traces_dir = tmp_path / "traces"
    tracker.base_dir.mkdir(parents=True, exist_ok=True)
    tracker.traces_dir.mkdir(parents=True, exist_ok=True)
    tracker.log_file = tracker.traces_dir / f"trace_{run_id}.log"
    tracker.events = []
    tracker.start_time = time.time()
    tracker.status = "Running"
    tracker.current_node = None
    return tracker


@pytest.fixture()
def tmp_tracker(tmp_path):
    """Create an ExecutionTracker whose files go to a temp directory."""
    return _make_tracker(tmp_path)


class TestExecutionTrackerFiles:
    def test_trace_log_created_in_traces_subdir(self, tmp_path):
        tracker = ExecutionTracker(run_id="abc12345", user_input="Test input")
        tracker.base_dir = tmp_path
        tracker.traces_dir = tmp_path / "traces"
        tracker.traces_dir.mkdir(parents=True, exist_ok=True)
        tracker.log_file = tracker.traces_dir / "trace_abc12345.log"
        tracker.log_trace("Sample trace entry")

        assert tracker.log_file.exists(), "Trace log file should exist in traces directory"
        assert tracker.log_file.parent.name == "traces"

    def test_tool_json_file_named_by_tool(self, tmp_path):
        tracker = _make_tracker(tmp_path, "runxyz1")
        tracker.track_tool_call(
            tool_name="flight_booking",
            input_params={"flight_id": "AI202"},
            output={"booking_id": "FLT-123"},
            status="completed",
        )

        tool_file = tmp_path / "flight_booking.json"
        assert tool_file.exists(), "runtime/flight_booking.json should be created"

        data = json.loads(tool_file.read_text())
        assert data["tool_name"] == "flight_booking"
        assert data["status"] == "completed"
        assert data["execution_count"] == 1
        assert data["current_call"]["input"]["flight_id"] == "AI202"
        assert data["current_call"]["result"]["booking_id"] == "FLT-123"

    def test_notification_tools_generate_dedicated_json(self, tmp_path):
        tracker = _make_tracker(tmp_path, "notif123")
        tracker.track_tool_call(
            tool_name="send_email_confirmation",
            input_params={"recipient": "user@example.com", "subject": "Booking"},
            output={"status": "sent", "success": True},
            status="completed",
        )
        tracker.track_tool_call(
            tool_name="send_sms_confirmation",
            input_params={"recipient": "+1234567890", "booking_id": "FLT-123"},
            output={"status": "sent", "message_status": "sent"},
            status="completed",
        )

        email_file = tmp_path / "send_email_confirmation.json"
        sms_file = tmp_path / "send_sms_confirmation.json"

        assert email_file.exists()
        assert sms_file.exists()

        email_data = json.loads(email_file.read_text())
        sms_data = json.loads(sms_file.read_text())

        assert email_data["tool_name"] == "send_email_confirmation"
        assert sms_data["tool_name"] == "send_sms_confirmation"


class TestEventRecording:
    def test_record_event_increments_count(self, tmp_tracker):
        initial = len(tmp_tracker.events)
        tmp_tracker.record_event("Test Event", "Node", "test_node", status="Success")
        assert len(tmp_tracker.events) == initial + 1

    def test_record_event_fields(self, tmp_tracker):
        tmp_tracker.record_event(
            event_type="Tool Call",
            component="Tool",
            component_name="search_flights",
            status="Success",
            input_payload={"origin": "DEL"},
            output_response=[{"flight": 1}],
        )
        evt = tmp_tracker.events[-1]
        assert evt["event_type"] == "Tool Call"
        assert evt["component_name"] == "search_flights"
        assert evt["status"] == "Success"
        assert evt["input_payload"]["origin"] == "DEL"


class TestNodeTracking:
    def test_track_node_start_sets_current_node(self, tmp_tracker):
        tmp_tracker.track_node_start("goal_understanding", {"user_input": "Japan trip"})
        assert tmp_tracker.current_node == "goal_understanding"

    def test_track_node_end_records_success(self, tmp_tracker):
        tmp_tracker.track_node_start("objective_planner", {})
        tmp_tracker.track_node_end("objective_planner", {}, {"pending_tool_calls": []}, status="Success")
        completed = [e for e in tmp_tracker.events if e["component_name"] == "objective_planner" and e["status"] == "Success"]
        assert len(completed) >= 1


class TestToolTracking:
    def test_track_tool_start_and_call(self, tmp_path):
        tracker = _make_tracker(tmp_path, "toolrun1")
        tracker.track_tool_start("search_flights", {"origin": "DEL", "destination": "TYO"})

        file_path = tmp_path / "search_flights.json"
        assert file_path.exists()
        data_started = json.loads(file_path.read_text())
        assert data_started["status"] == "started"

        tracker.track_tool_call(
            tool_name="search_flights",
            input_params={"origin": "DEL", "destination": "TYO"},
            output=[{"airline": "Air India", "price": 45000}],
            status="completed",
        )
        data_completed = json.loads(file_path.read_text())
        assert data_completed["status"] == "completed"
        assert data_completed["execution_count"] == 1


class TestWorkflowCompletion:
    def test_complete_success_updates_status(self, tmp_tracker):
        tmp_tracker.track_workflow_complete(success=True)
        assert tmp_tracker.status == "Success"
