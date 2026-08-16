"""ToolExecutionNode — Resolves and executes a single tool selected by ReactNode.

Reads pending_tool_call from state, looks up the tool in TOOL_REGISTRY,
executes it, and appends the result to tool_observations.

On success or failure, always routes back to ReactNode so ReAct can
decide the next step — there is no separate meta-reasoner.
"""

from __future__ import annotations

import importlib
import logging
import time
from typing import Any

from graph.state import TripState
from app.settings import TOOL_REGISTRY
from app.tracing import get_tracker
from graph.tool_selection_memory import ToolSelectionMemory

logger = logging.getLogger(__name__)


def tool_execution(state: TripState) -> dict[str, Any]:
    """Execute the pending tool call and record the observation."""
    pending = state.get("pending_tool_call", {})
    tracker = get_tracker()

    if not pending or not pending.get("tool"):
        logger.warning("tool_execution: no pending_tool_call found")
        return {"pending_tool_call": {}}

    tool_name: str = pending["tool"]
    arguments: dict = pending.get("arguments", pending.get("parameters", {}))
    reasoning: str = pending.get("reasoning", "")

    observations = list(state.get("tool_observations", []))
    tsm_data = dict(state.get("tool_selection_memory", {}))
    tsm = ToolSelectionMemory(tsm_data)

    module_path = TOOL_REGISTRY.get(tool_name)
    if not module_path:
        error_msg = f"Tool '{tool_name}' not found in TOOL_REGISTRY."
        logger.error("tool_execution: %s", error_msg)
        observations.append(_make_obs(tool_name, arguments, None, "error", error_msg))
        tsm.record(tool_name, success=False, latency=0.0)
        if tracker:
            tracker.track_tool_call(tool_name, arguments, None, status="failed", error=error_msg)
        return {
            "tool_observations": observations,
            "tool_selection_memory": tsm.data,
            "pending_tool_call": {},
        }

    # Record real-time tool start in runtime/<tool_name>.json
    if tracker:
        tracker.track_tool_start(tool_name, arguments)

    start = time.time()
    try:
        module = importlib.import_module(module_path)
        tool_fn = getattr(module, tool_name, None)
        if not tool_fn:
            raise AttributeError(f"Function '{tool_name}' not found in module '{module_path}'.")
        result = tool_fn(**arguments)
        latency = time.time() - start

        observations.append(_make_obs(tool_name, arguments, result, "success"))
        tsm.record(tool_name, success=True, latency=latency)

        logger.info(
            "tool_execution: tool=%s  status=success  latency=%.2fs",
            tool_name, latency,
        )
        if tracker:
            tracker.track_tool_call(tool_name, arguments, result, status="completed")

    except Exception as exc:
        latency = time.time() - start
        error_msg = str(exc)
        result = None
        observations.append(_make_obs(tool_name, arguments, None, "error", error_msg))
        tsm.record(tool_name, success=False, latency=latency)

        logger.error(
            "tool_execution: tool=%s  error=%s", tool_name, error_msg
        )
        if tracker:
            tracker.track_tool_call(tool_name, arguments, None, status="failed", error=error_msg)

    # Accumulate booking / payment results
    booking_results = list(state.get("booking_results", []))
    payment_results = list(state.get("payment_results", []))

    if tool_name in ("book_flight", "flight_booking", "book_hotel", "hotel_booking", "book_train", "train_booking", "make_reservation") and isinstance(result, dict) and result.get("booking_id"):
        booking_results.append(result)

    if tool_name in ("process_payment", "payment") and isinstance(result, dict) and result.get("transaction_id"):
        payment_results.append(result)

    return {
        "tool_observations": observations,
        "tool_selection_memory": tsm.data,
        "booking_results": booking_results,
        "payment_results": payment_results,
        "pending_tool_call": {},
    }


def _make_obs(
    tool: str,
    args: dict,
    result: Any,
    status: str,
    error: str | None = None,
) -> dict:
    obs: dict[str, Any] = {
        "tool": tool,
        "arguments": args,
        "result": result,
        "status": status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if error:
        obs["error"] = error
    return obs
