"""Action Dispatcher node.

Executes approved booking, payment, and reservation actions.
Only runs if approval_status == "approved" or "not_needed".
Results are validated against BookingConfirmation / ReservationConfirmation
/ PaymentReceipt schemas from schemas.approval_schema.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.state import TripState
from schemas.approval_schema import ApprovalStatus
from tools.booking import book_flight, book_hotel
from tools.reservation import make_reservation
from tools.payment import process_payment
from app.tracing import get_tracker

logger = logging.getLogger(__name__)

# Tool function registry for booking / payment actions
_ACTION_FUNCTIONS: dict[str, Any] = {
    "book_flight": book_flight,
    "book_hotel": book_hotel,
    "make_reservation": make_reservation,
    "process_payment": process_payment,
}


def action_dispatcher(state: TripState) -> dict[str, Any]:
    """Execute approved booking / payment actions."""
    approval_status = state.get("approval_status", "")

    if approval_status not in (ApprovalStatus.APPROVED, ApprovalStatus.NOT_NEEDED):
        logger.warning(
            "action_dispatcher: Skipping — approval_status=%s", approval_status
        )
        return {
            "booking_results": state.get("booking_results", []),
            "payment_results": state.get("payment_results", []),
        }

    pending = state.get("pending_tool_calls", [])
    booking_results = list(state.get("booking_results", []))
    payment_results = list(state.get("payment_results", []))
    errors = list(state.get("errors", []))
    tracker = get_tracker()

    # Filter to only booking / payment actions
    booking_actions = [
        call for call in pending
        if call.get("tool", "") in _ACTION_FUNCTIONS
    ]

    logger.info("action_dispatcher: Executing %d action(s).", len(booking_actions))

    for call in booking_actions:
        tool_name = call.get("tool", "")
        params = call.get("parameters", {})

        func = _ACTION_FUNCTIONS.get(tool_name)
        if func is None:
            error_msg = f"Unknown action: {tool_name}"
            errors.append({"tool": tool_name, "error": error_msg})
            if tracker:
                tracker.track_tool_call(
                    tool_name=tool_name,
                    input_params=params,
                    output=None,
                    status="Failed",
                    error=error_msg,
                    node_name="action_dispatcher",
                )
            continue

        try:
            result = func(**params)
            logger.info("action_dispatcher: %s succeeded — id=%s", tool_name, result.get("booking_id") or result.get("transaction_id") or result.get("reservation_id", ""))

            if tool_name == "process_payment":
                payment_results.append(result)
            else:
                booking_results.append(result)

            if tracker:
                tracker.track_tool_call(
                    tool_name=tool_name,
                    input_params=params,
                    output=result,
                    status="Success",
                    node_name="action_dispatcher",
                )

        except Exception as exc:
            error_msg = f"Action {tool_name} failed: {exc!s}"
            logger.error(error_msg, exc_info=True)
            errors.append({
                "tool": tool_name,
                "error": error_msg,
                "params": params,
            })
            if tracker:
                tracker.track_tool_call(
                    tool_name=tool_name,
                    input_params=params,
                    output=None,
                    status="Failed",
                    error=error_msg,
                    node_name="action_dispatcher",
                )

    # Remove executed booking actions from pending so they aren't re-dispatched
    remaining = [
        call for call in pending
        if call.get("tool", "") not in _ACTION_FUNCTIONS
    ]

    return {
        "booking_results": booking_results,
        "payment_results": payment_results,
        "pending_tool_calls": remaining,
        "errors": errors,
    }
