"""Capability Dispatcher node.

Pure routing logic — no LLM call. Reads pending_tool_calls from state,
invokes the appropriate tool functions, collects results, and logs tool execution.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.state import TripState
from tools.travel_research import search_flights, search_hotels
from tools.weather import get_weather
from tools.constraint_checker import check_constraints
from app.tracing import get_tracker

logger = logging.getLogger(__name__)

# Tool function registry
_TOOL_FUNCTIONS: dict[str, Any] = {
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "get_weather": get_weather,
    "check_constraints": check_constraints,
}


def capability_dispatcher(state: TripState) -> dict:
    """Dispatch pending tool calls and collect results."""
    pending = state.get("pending_tool_calls", [])
    existing_results = dict(state.get("tool_results", {}))
    errors = list(state.get("errors", []))

    logger.info("capability_dispatcher  pending_calls=%d", len(pending))
    tracker = get_tracker()

    for call in pending:
        tool_name = call.get("tool", "")
        params = call.get("parameters", {})
        sub_goal_id = call.get("sub_goal_id", "")

        logger.info(
            "Dispatching  tool=%s  params=%s  sub_goal=%s",
            tool_name, params, sub_goal_id,
        )

        func = _TOOL_FUNCTIONS.get(tool_name)
        if func is None:
            error_msg = f"Unknown tool: {tool_name}"
            logger.warning(error_msg)
            errors.append({"tool": tool_name, "error": error_msg})
            if tracker:
                tracker.track_tool_call(
                    tool_name=tool_name,
                    input_params=params,
                    output=None,
                    status="Failed",
                    error=error_msg,
                    node_name="capability_dispatcher",
                )
            continue

        try:
            result = func(**params)
            key = tool_name
            if key in existing_results:
                if isinstance(existing_results[key], list) and isinstance(result, list):
                    existing_results[key] = existing_results[key] + result
                else:
                    existing_results[key] = result
            else:
                existing_results[key] = result

            if tracker:
                tracker.track_tool_call(
                    tool_name=tool_name,
                    input_params=params,
                    output=result,
                    status="Success",
                    node_name="capability_dispatcher",
                )

            logger.info(
                "Tool %s returned %d items",
                tool_name,
                len(result) if isinstance(result, list) else 1,
            )
        except Exception as exc:
            error_msg = f"Tool {tool_name} failed: {exc!s}"
            logger.error(error_msg, exc_info=True)
            errors.append({"tool": tool_name, "error": error_msg, "params": params})
            if tracker:
                tracker.track_tool_call(
                    tool_name=tool_name,
                    input_params=params,
                    output=None,
                    status="Failed",
                    error=error_msg,
                    node_name="capability_dispatcher",
                )

    return {
        "tool_results": existing_results,
        "pending_tool_calls": [],
        "errors": errors,
    }
