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
from app.settings import TOOL_REGISTRY, get_canonical_tool_name
from app.tracing import get_tracker
from graph.tool_selection_memory import ToolSelectionMemory

logger = logging.getLogger(__name__)


def _validate_and_reconcile_booking_payload(tool_name: str, arguments: dict, state: TripState) -> dict:
    """Validate and reconcile booking tool arguments against latest confirmed TripState.

    Guarantees that:
      1. Check-in/check-out or journey dates in arguments strictly match extracted_entities.
      2. Mismatched or stale default dates (e.g. 2026-08-20 when state has 2026-08-22) are overridden to match latest state.
      3. Selected hotel/train/flight and passenger/guest details are preserved.
    """
    reconciled = dict(arguments)
    entities = state.get("extracted_entities", {})
    guest_info = state.get("guest_info", {})
    passenger_info = state.get("passenger_info", [])
    selected = state.get("selected_booking", {})

    state_start_date = entities.get("start_date") or guest_info.get("checkin_date") or selected.get("date")
    state_end_date = entities.get("end_date") or guest_info.get("checkout_date")

    if tool_name in ("book_hotel", "hotel_booking"):
        if state_start_date:
            reconciled["checkin_date"] = state_start_date
        if state_end_date:
            reconciled["checkout_date"] = state_end_date
        if not reconciled.get("hotel_name") and selected.get("hotel_name"):
            reconciled["hotel_name"] = selected.get("hotel_name")
        if not reconciled.get("guest_info") and guest_info:
            reconciled["guest_info"] = guest_info

    elif tool_name in ("book_train", "train_booking", "book_flight", "flight_booking"):
        if state_start_date:
            reconciled["date"] = state_start_date
        if not reconciled.get("passengers") and passenger_info:
            reconciled["passengers"] = passenger_info

    logger.info("_validate_and_reconcile_booking_payload [%s]: arguments reconciled=%s", tool_name, reconciled)
    return reconciled


def tool_execution(state: TripState) -> dict[str, Any]:
    """Execute the pending tool call and record the observation."""
    pending = state.get("pending_tool_call", {})
    tracker = get_tracker()

    if not pending or not pending.get("tool"):
        logger.warning("tool_execution: no pending_tool_call found")
        return {"pending_tool_call": {}}

    raw_tool_name: str = pending["tool"]
    tool_name: str = get_canonical_tool_name(raw_tool_name)
    arguments: dict = pending.get("arguments", pending.get("parameters", {}))
    reasoning: str = pending.get("reasoning", "")

    if tool_name in ("book_hotel", "hotel_booking", "book_train", "train_booking", "book_flight", "flight_booking"):
        arguments = _validate_and_reconcile_booking_payload(tool_name, arguments, state)

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

    # Accumulate booking / payment results & advance sequential booking queue
    booking_results = list(state.get("booking_results", []))
    payment_results = list(state.get("payment_results", []))
    booking_queue = list(state.get("booking_queue", []))
    current_index = state.get("current_booking_index", 0)

    if tool_name in ("book_flight", "flight_booking", "book_hotel", "hotel_booking", "book_train", "train_booking", "make_reservation") and isinstance(result, dict) and result.get("booking_id"):
        booking_results.append(result)
        if booking_queue and current_index < len(booking_queue):
            current_index += 1

    if tool_name in ("process_payment", "payment") and isinstance(result, dict) and result.get("transaction_id"):
        payment_results.append(result)

    return {
        "tool_observations": observations,
        "tool_selection_memory": tsm.data,
        "booking_results": booking_results,
        "payment_results": payment_results,
        "booking_queue": booking_queue,
        "current_booking_index": current_index,
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
