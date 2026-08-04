"""Comprehensive Debugging & Observability System.

Generates two separate files for every execution in the runtime/ directory:
1. runtime_<run_id>.json — Full structured JSON event log (tools, state changes, errors, etc.)
2. trace_<run_id>.log — Human-readable execution log focused on tool calls & workflow progression.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

# Context variable to hold active tracker for current thread/async context
_current_tracker: ContextVar[Optional[ExecutionTracker]] = ContextVar(
    "_current_tracker", default=None
)


def get_tracker() -> Optional[ExecutionTracker]:
    """Get current active ExecutionTracker, if any."""
    return _current_tracker.get()


def set_tracker(tracker: Optional[ExecutionTracker]) -> None:
    """Set active ExecutionTracker."""
    _current_tracker.set(tracker)


class ExecutionTracker:
    """Manages dual-file observability for workflow runs.

    Files generated:
      - runtime/runtime_<run_id>.json
      - runtime/trace_<run_id>.log
    """

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or uuid.uuid4().hex[:8]
        self.base_dir = Path(__file__).resolve().parent.parent / "runtime"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.json_file = self.base_dir / f"runtime_{self.run_id}.json"
        self.log_file = self.base_dir / f"trace_{self.run_id}.log"

        self.events: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.status = "Started"
        self.current_node: Optional[str] = None

        # Clean old log/json if re-using same ID
        if self.json_file.exists():
            self.json_file.unlink()
        if self.log_file.exists():
            self.log_file.unlink()

        # Initial event
        self.record_event(
            event_type="Agent Initialization",
            component="Agent",
            component_name="AtlasAI",
            status="Started",
            metadata={"run_id": self.run_id},
        )
        self.log_trace(f"[Workflow] Initialized (Run ID: {self.run_id})\n")

    def record_event(
        self,
        event_type: str,
        component: str,
        component_name: str,
        current_workflow_node: Optional[str] = None,
        input_payload: Optional[Any] = None,
        output_response: Optional[Any] = None,
        status: str = "Success",
        state_changes: Optional[Dict[str, Any]] = None,
        context_variables: Optional[Dict[str, Any]] = None,
        error_details: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a structured runtime event and write to JSON."""
        node = current_workflow_node or self.current_node
        event = {
            "event_id": f"evt_{len(self.events) + 1}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event_type": event_type,
            "component": component,
            "component_name": component_name,
            "current_workflow_node": node,
            "status": status,
            "input_payload": _serialize(input_payload),
            "output_response": _serialize(output_response),
            "state_changes": _serialize(state_changes),
            "context_variables": _serialize(context_variables),
            "error_details": _serialize(error_details),
            "metadata": _serialize(metadata),
        }
        self.events.append(event)
        self._flush_json()
        return event

    def log_trace(self, text: str) -> None:
        """Append line to trace log."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    def track_node_start(self, node_name: str, input_state: Dict[str, Any]) -> None:
        """Record node execution start."""
        self.current_node = node_name
        self.record_event(
            event_type="Node Execution",
            component="Node",
            component_name=node_name,
            current_workflow_node=node_name,
            status="Started",
            input_payload={"state_keys": list(input_state.keys()) if isinstance(input_state, dict) else None},
        )
        pretty_name = "".join(x.title() for x in node_name.split("_"))
        self.log_trace(f"[{pretty_name}] Started")

    def track_node_end(
        self,
        node_name: str,
        state_before: Dict[str, Any],
        state_update: Dict[str, Any],
        status: str = "Success",
        error: Optional[Any] = None,
    ) -> None:
        """Record node execution completion."""
        pretty_name = "".join(x.title() for x in node_name.split("_"))

        # Log planned tool selections if planner produced pending calls
        if isinstance(state_update, dict) and "pending_tool_calls" in state_update:
            pending = state_update["pending_tool_calls"]
            for call in pending:
                tool = call.get("tool", "Unknown")
                pretty_tool = "".join(x.title() for x in tool.split("_"))
                self.log_trace(f"[{pretty_name}] Selected: {pretty_tool} Tool")

        state_changes = {
            "update_keys": list(state_update.keys()) if isinstance(state_update, dict) else None,
            "update_summary": _summarize_update(state_update),
        }

        self.record_event(
            event_type="Node Execution",
            component="Node",
            component_name=node_name,
            current_workflow_node=node_name,
            status=status,
            output_response=state_update,
            state_changes=state_changes,
            error_details=error,
        )

        if status != "Success":
            self.log_trace(f"[{pretty_name}] Failed: {error}\n")

    def track_tool_call(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output: Any,
        status: str = "Success",
        error: Optional[Any] = None,
        node_name: Optional[str] = None,
    ) -> None:
        """Record tool invocation."""
        node = node_name or self.current_node
        pretty_tool = "".join(x.title() for x in tool_name.split("_"))

        self.record_event(
            event_type="Tool Call",
            component="Tool",
            component_name=tool_name,
            current_workflow_node=node,
            status=status,
            input_payload=input_params,
            output_response=output,
            error_details=error,
        )

        # Output summary calculation
        output_summary = _summarize_tool_output(output)

        self.log_trace(f"[Tool] {pretty_tool}")
        self.log_trace(f"        Input  : {json.dumps(input_params, default=str)}")
        self.log_trace(f"        Status : {status}")
        self.log_trace(f"        Output : {output_summary}\n")

    def track_routing(self, from_node: str, to_node: str) -> None:
        """Record routing decision."""
        pretty_to = "".join(x.title() for x in to_node.split("_"))
        self.record_event(
            event_type="Conditional Routing",
            component="Router",
            component_name="Router",
            current_workflow_node=from_node,
            status="Success",
            input_payload={"from": from_node},
            output_response={"to": to_node},
        )
        self.log_trace(f"[Router] → {pretty_to} Node\n")

    def track_memory_op(
        self, op_type: str, category_or_key: str, payload: Any
    ) -> None:
        """Record memory read/write operation."""
        self.record_event(
            event_type="Memory Operation",
            component="Memory",
            component_name=op_type,
            status="Success",
            input_payload={"key": category_or_key, "data": payload},
        )
        self.log_trace(f"[Memory] {op_type}: {category_or_key}")

    def track_workflow_complete(
        self, success: bool = True, error: Optional[Any] = None
    ) -> None:
        """Record workflow completion."""
        self.status = "Success" if success else "Failed"
        self.record_event(
            event_type="Workflow Completion",
            component="Agent",
            component_name="AtlasAI",
            status=self.status,
            error_details=error,
        )
        if success:
            self.log_trace("[Workflow] Completed Successfully")
        else:
            self.log_trace(f"[Workflow] Failed: {error}")
        self._flush_json()

    def _flush_json(self) -> None:
        """Flush JSON data to disk."""
        data = {
            "run_id": self.run_id,
            "status": self.status,
            "start_time": datetime.datetime.fromtimestamp(self.start_time, datetime.timezone.utc).isoformat(),
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_events": len(self.events),
            "events": self.events,
        }
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)


def start_execution_tracker(run_id: Optional[str] = None) -> ExecutionTracker:
    """Helper to start and register an ExecutionTracker."""
    tracker = ExecutionTracker(run_id=run_id)
    set_tracker(tracker)
    return tracker


class RuntimeTracer(BaseCallbackHandler):
    """LangChain callback handler to stream LLM events into ExecutionTracker."""

    def __init__(self, run_id: Optional[str] = None, tracker: Optional[ExecutionTracker] = None):
        super().__init__()
        self.tracker = tracker or get_tracker() or start_execution_tracker(run_id=run_id)

    def on_chat_model_start(
        self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs: Any
    ) -> Any:
        prompt_texts = []
        for message_list in messages:
            for msg in message_list:
                prompt_texts.append(f"[{msg.type.upper()}]: {msg.content}")

        self.tracker.record_event(
            event_type="LLM Call",
            component="Service",
            component_name=(serialized or {}).get("name", "ChatModel"),
            status="Started",
            input_payload={"prompts": prompt_texts},
        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        outputs = []
        for gen_list in response.generations:
            for gen in gen_list:
                outputs.append(gen.text)

        self.tracker.record_event(
            event_type="LLM Call",
            component="Service",
            component_name="ChatModel",
            status="Success",
            output_response={"outputs": outputs},
        )

    def on_llm_error(
        self, error: BaseException, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> Any:
        self.tracker.record_event(
            event_type="LLM Call",
            component="Service",
            component_name="ChatModel",
            status="Failed",
            error_details=str(error),
        )


def _serialize(obj: Any) -> Any:
    """Convert non-serializable objects to dict/str representation."""
    if obj is None or isinstance(obj, (int, float, str, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize(x) for x in obj]
    if hasattr(obj, "model_dump"):
        return _serialize(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return _serialize(obj.__dict__)
    return str(obj)


def _summarize_update(update: Any) -> Any:
    """Create short summary of state update."""
    if not isinstance(update, dict):
        return str(update)[:100]
    summary = {}
    for k, v in update.items():
        if isinstance(v, list):
            summary[k] = f"list (len={len(v)})"
        elif isinstance(v, dict):
            summary[k] = f"dict (keys={list(v.keys())})"
        else:
            summary[k] = str(v)[:60]
    return summary


def _summarize_tool_output(output: Any) -> str:
    """Summarize tool output for concise trace log."""
    if isinstance(output, list):
        return f"{len(output)} items returned"
    if isinstance(output, dict):
        if "booking_id" in output:
            return f"Booking Confirmed ({output['booking_id']})"
        if "transaction_id" in output:
            return f"Payment Processed ({output['transaction_id']})"
        if "reservation_id" in output:
            return f"Reservation Confirmed ({output['reservation_id']})"
        return f"Returned dict with keys: {list(output.keys())}"
    return str(output)[:100]
