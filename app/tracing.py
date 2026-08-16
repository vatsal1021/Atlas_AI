"""Comprehensive Debugging & Observability System.

Runtime Telemetry & Observability Rules:
  1. Tool Runtime JSON files MUST be named directly after the tool:
     runtime/<tool_name>.json (e.g. runtime/flight_booking.json, runtime/payment.json).
     No run IDs, timestamps, or session IDs in JSON filenames.
  2. Each tool has ONE persistent JSON file updated in real-time across invocations.
  3. Missing tool JSON files are created automatically.
  4. ALL trace logs exist ONLY inside runtime/traces/ (e.g. runtime/traces/trace_<run_id>.log).
"""

from __future__ import annotations

import datetime
import json
import logging
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

# Context variable holds the active tracker for the current thread / async task
_current_tracker: ContextVar[Optional["ExecutionTracker"]] = ContextVar(
    "_current_tracker", default=None
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_tracker() -> ExecutionTracker:
    """Return the active ExecutionTracker, auto-initializing a default one if none exists."""
    tracker = _current_tracker.get()
    if tracker is None:
        tracker = ExecutionTracker(run_id="active_run", user_input="Execution run")
        _current_tracker.set(tracker)
    return tracker


def set_tracker(tracker: Optional["ExecutionTracker"]) -> None:
    """Register an ExecutionTracker as active for the current context."""
    _current_tracker.set(tracker)


def start_execution_tracker(
    run_id: Optional[str] = None,
    user_input: Optional[str] = None,
) -> "ExecutionTracker":
    """Create, register, and return a new ExecutionTracker for this run."""
    tracker = ExecutionTracker(run_id=run_id, user_input=user_input)
    set_tracker(tracker)
    return tracker


# ---------------------------------------------------------------------------
# Core ExecutionTracker
# ---------------------------------------------------------------------------

class ExecutionTracker:
    """Manages observability and tool-specific telemetry.

    Files structure in ``runtime/``:
      - ``runtime/<tool_name>.json``      — One persistent JSON file per tool name
      - ``runtime/traces/trace_<id>.log`` — Human-readable trace logs
    """

    def __init__(
        self,
        run_id: Optional[str] = None,
        user_input: Optional[str] = None,
    ):
        self.run_id = run_id or uuid.uuid4().hex[:8]
        self.user_input = user_input or ""
        self.base_dir = Path(__file__).resolve().parent.parent / "runtime"
        self.traces_dir = self.base_dir / "traces"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.traces_dir / f"trace_{self.run_id}.log"

        self.events: List[Dict[str, Any]] = []
        self.start_time: float = time.time()
        self.status: str = "Running"
        self.current_node: Optional[str] = None

        # Clean up legacy files directly under runtime/ if any exist
        for legacy_json in self.base_dir.glob("runtime_*.json"):
            try:
                legacy_json.unlink()
            except Exception:
                pass
        for legacy_log in self.base_dir.glob("*.log"):
            try:
                legacy_log.unlink()
            except Exception:
                pass

        # Trace header
        started_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        divider = "═" * 60
        self.log_trace(divider)
        self.log_trace(f"  AtlasAI Execution Trace")
        self.log_trace(f"  Run ID  : {self.run_id}")
        self.log_trace(f"  Started : {started_str}")
        if self.user_input:
            self.log_trace(f"  Request : {self.user_input[:120]}")
        self.log_trace(divider)
        self.log_trace("")

        # Seed initial event
        self.record_event(
            event_type="Agent Initialization",
            component="Agent",
            component_name="AtlasAI",
            status="Started",
            metadata={
                "run_id": self.run_id,
                "user_input": self.user_input,
            },
        )
        self.log_trace(f"[Workflow] Run {self.run_id} started\n")

    # -----------------------------------------------------------------------
    # Low-level event recorder & trace logger
    # -----------------------------------------------------------------------

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
        """Append a structured event to memory."""
        node = current_workflow_node or self.current_node
        event: Dict[str, Any] = {
            "event_id": f"evt_{len(self.events) + 1:04d}",
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
        return event

    def log_trace(self, text: str) -> None:
        """Append a line to the human-readable trace log under runtime/traces/."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    # -----------------------------------------------------------------------
    # High-level tracking helpers
    # -----------------------------------------------------------------------

    def track_node_start(self, node_name: str, input_state: Dict[str, Any]) -> None:
        """Log the beginning of a LangGraph node execution."""
        self.current_node = node_name
        self.record_event(
            event_type="Node Execution",
            component="Node",
            component_name=node_name,
            status="Started",
            input_payload={
                "state_keys": list(input_state.keys()) if isinstance(input_state, dict) else None,
            },
        )
        self.log_trace(f"[{_pretty(node_name)}] Started")

    def track_node_end(
        self,
        node_name: str,
        state_before: Dict[str, Any],
        state_update: Dict[str, Any],
        status: str = "Success",
        error: Optional[Any] = None,
    ) -> None:
        """Log the completion of a LangGraph node execution."""
        if isinstance(state_update, dict):
            for call in state_update.get("pending_tool_calls", []):
                tool = call.get("tool", "Unknown")
                self.log_trace(f"[{_pretty(node_name)}] Selected: {_pretty(tool)} Tool")

        state_changes = {
            "update_keys": list(state_update.keys()) if isinstance(state_update, dict) else None,
            "update_summary": _summarize_update(state_update),
        }

        self.record_event(
            event_type="Node Execution",
            component="Node",
            component_name=node_name,
            status=status,
            output_response=state_update,
            state_changes=state_changes,
            error_details=error,
        )

        status_label = "✓ Success" if status == "Success" else f"✗ {status}"
        if status == "Failed":
            self.log_trace(f"[{_pretty(node_name)}] {status_label}: {error}\n")
        else:
            self.log_trace(f"[{_pretty(node_name)}] {status_label}\n")

    def track_tool_start(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        node_name: Optional[str] = None,
    ) -> None:
        """Log tool execution start in real-time into runtime/<tool_name>.json."""
        node = node_name or self.current_node
        self.record_event(
            event_type="Tool Call",
            component="Tool",
            component_name=tool_name,
            current_workflow_node=node,
            status="Started",
            input_payload=input_params,
            metadata={"node": node},
        )
        self._flush_tool_json(
            tool_name=tool_name,
            input_params=input_params,
            output=None,
            status="started",
            error=None,
            node_name=node,
        )

    def track_tool_call(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output: Any,
        status: str = "Success",
        error: Optional[Any] = None,
        node_name: Optional[str] = None,
    ) -> None:
        """Log tool invocation completion/failure in runtime/<tool_name>.json."""
        node = node_name or self.current_node
        event_status = "Success" if status.lower() in ("success", "completed") else "Failed"
        self.record_event(
            event_type="Tool Call",
            component="Tool",
            component_name=tool_name,
            current_workflow_node=node,
            status=event_status,
            input_payload=input_params,
            output_response=output,
            error_details=error,
            metadata={"node": node},
        )

        # Update dedicated tool JSON file (runtime/<tool_name>.json)
        self._flush_tool_json(
            tool_name=tool_name,
            input_params=input_params,
            output=output,
            status=status,
            error=error,
            node_name=node,
        )

        # Human-readable trace block
        params_str = json.dumps(input_params, default=str)
        if len(params_str) > 200:
            params_str = params_str[:197] + "..."
        output_summary = _summarize_tool_output(output) if event_status == "Success" else f"ERROR: {error}"

        self.log_trace(f"[Tool] {_pretty(tool_name)}")
        self.log_trace(f"       Input  : {params_str}")
        self.log_trace(f"       Status : {status}")
        self.log_trace(f"       Output : {output_summary}\n")

    def track_routing(self, from_node: str, to_node: str) -> None:
        """Log a conditional routing decision."""
        self.record_event(
            event_type="Conditional Routing",
            component="Router",
            component_name="Router",
            current_workflow_node=from_node,
            status="Success",
            input_payload={"from": from_node},
            output_response={"to": to_node},
        )
        self.log_trace(f"[Router] → {_pretty(to_node)} Node\n")

    def track_memory_op(
        self,
        op_type: str,
        category_or_key: str,
        payload: Any,
    ) -> None:
        """Log a memory read or write operation."""
        self.record_event(
            event_type="Memory Operation",
            component="Memory",
            component_name=op_type,
            status="Success",
            input_payload={"key": category_or_key},
            output_response=_serialize(payload),
        )
        self.log_trace(f"[Memory] {op_type}: {category_or_key}")

    def track_workflow_complete(
        self,
        success: bool = True,
        error: Optional[Any] = None,
    ) -> None:
        """Record final workflow status and trace log footer."""
        elapsed = time.time() - self.start_time
        self.status = "Success" if success else "Failed"

        self.record_event(
            event_type="Workflow Completion",
            component="Agent",
            component_name="AtlasAI",
            status=self.status,
            error_details=error,
            metadata={"elapsed_seconds": round(elapsed, 2)},
        )

        # Trace footer
        self.log_trace("")
        divider = "═" * 60
        self.log_trace(divider)
        if success:
            self.log_trace(f"[Workflow] Completed Successfully  ({elapsed:.1f}s)")
        else:
            self.log_trace(f"[Workflow] Failed  ({elapsed:.1f}s)")
            if error:
                self.log_trace(f"           Error: {error}")

        tool_events    = [e for e in self.events if e["event_type"] == "Tool Call"]
        node_events    = [e for e in self.events if e["event_type"] == "Node Execution" and e["status"] == "Started"]
        error_events   = [e for e in self.events if e.get("error_details")]
        llm_events     = [e for e in self.events if e["event_type"] == "LLM Call" and e["status"] == "Success"]
        mem_events     = [e for e in self.events if e["event_type"] == "Memory Operation"]

        self.log_trace(f"")
        self.log_trace(f"  Summary:")
        self.log_trace(f"    Nodes executed  : {len(node_events)}")
        self.log_trace(f"    Tool calls      : {len(tool_events)}")
        self.log_trace(f"    LLM calls       : {len(llm_events)}")
        self.log_trace(f"    Memory ops      : {len(mem_events)}")
        self.log_trace(f"    Errors          : {len(error_events)}")
        self.log_trace(divider)
        self.log_trace(f"  Trace Log : {self.log_file}")
        self.log_trace(divider)

    # -----------------------------------------------------------------------
    # Real-Time Tool-Specific JSON Generator
    # -----------------------------------------------------------------------

    def _flush_tool_json(
        self,
        tool_name: str,
        input_params: Any,
        output: Any,
        status: str,
        error: Optional[Any],
        node_name: Optional[str],
    ) -> None:
        """Create/update runtime/<tool_name>.json continuously in real-time."""
        # Sanitize tool_name to build valid filename directly under runtime/
        clean_tool_name = tool_name.strip().lower()
        tool_file = self.base_dir / f"{clean_tool_name}.json"

        existing_data: Dict[str, Any] = {}
        if tool_file.exists():
            try:
                with open(tool_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = {}

        execution_count = existing_data.get("execution_count", 0)
        errors = existing_data.get("errors", [])
        if not isinstance(errors, list):
            errors = []

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        is_started = (status.lower() == "started")
        is_success = (status.lower() in ("completed", "success"))

        prev_status = existing_data.get("status", "")

        if is_started:
            execution_count += 1
            final_status = "started"
        elif is_success:
            if prev_status != "started":
                execution_count += 1
            final_status = "completed"
        else:
            if prev_status != "started":
                execution_count += 1
            final_status = "failed"

        if error:
            errors.append({
                "error": _serialize(error),
                "timestamp": now_iso,
                "input": _serialize(input_params),
            })

        current_call = {
            "input": _serialize(input_params),
            "result": _serialize(output),
            "success": is_success if not is_started else None,
            "timestamp": now_iso,
            "node": node_name or self.current_node,
        }

        last_result = _serialize(output) if is_success else existing_data.get("last_result")

        tool_json_data = {
            "tool_name": clean_tool_name,
            "status": final_status,
            "current_call": current_call,
            "last_result": last_result,
            "errors": errors,
            "execution_count": execution_count,
            "last_updated": now_iso,
        }

        with open(tool_file, "w", encoding="utf-8") as f:
            json.dump(tool_json_data, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# LangChain callback — captures LLM calls automatically
# ---------------------------------------------------------------------------

class RuntimeTracer(BaseCallbackHandler):
    """LangChain callback handler that forwards LLM events to ExecutionTracker."""

    def __init__(
        self,
        run_id: Optional[str] = None,
        tracker: Optional[ExecutionTracker] = None,
    ):
        super().__init__()
        self.tracker = tracker or get_tracker() or start_execution_tracker(run_id=run_id)

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        **kwargs: Any,
    ) -> Any:
        prompts: List[str] = []
        for msg_list in messages:
            for msg in msg_list:
                preview = str(msg.content)[:300]
                prompts.append(f"[{msg.type.upper()}]: {preview}")

        self.tracker.record_event(
            event_type="LLM Call",
            component="Service",
            component_name=(serialized or {}).get("name", "ChatModel"),
            current_workflow_node=self.tracker.current_node,
            status="Started",
            input_payload={"prompts": prompts},
        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        outputs: List[str] = []
        for gen_list in response.generations:
            for gen in gen_list:
                outputs.append(str(gen.text)[:300])

        self.tracker.record_event(
            event_type="LLM Call",
            component="Service",
            component_name="ChatModel",
            current_workflow_node=self.tracker.current_node,
            status="Success",
            output_response={"outputs": outputs},
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self.tracker.record_event(
            event_type="LLM Call",
            component="Service",
            component_name="ChatModel",
            current_workflow_node=self.tracker.current_node,
            status="Failed",
            error_details=str(error),
        )


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """Recursively convert non-JSON-serialisable objects."""
    if obj is None or isinstance(obj, (int, float, str, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize(x) for x in obj]
    if hasattr(obj, "model_dump"):        # Pydantic v2
        return _serialize(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return _serialize(obj.__dict__)
    return str(obj)


def _pretty(snake: str) -> str:
    """Convert snake_case to TitleCase for trace log readability."""
    return "".join(x.title() for x in snake.split("_"))


def _summarize_update(update: Any) -> Any:
    """Compact representation of a state update dict."""
    if not isinstance(update, dict):
        return str(update)[:120]
    summary: Dict[str, str] = {}
    for k, v in update.items():
        if isinstance(v, list):
            summary[k] = f"list({len(v)})"
        elif isinstance(v, dict):
            summary[k] = f"dict(keys={list(v.keys())})"
        else:
            summary[k] = str(v)[:80]
    return summary


def _summarize_tool_output(output: Any) -> str:
    """One-line summary of a tool's return value for the trace log."""
    if isinstance(output, list):
        return f"{len(output)} items returned"
    if isinstance(output, dict):
        if "booking_id" in output:
            return f"Booking Confirmed — {output['booking_id']}"
        if "transaction_id" in output:
            return f"Payment Processed — {output['transaction_id']}"
        if "reservation_id" in output:
            return f"Reservation Confirmed — {output['reservation_id']}"
        return f"dict with keys: {list(output.keys())}"
    return str(output)[:120]
