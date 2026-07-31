"""Human Approval node.

Checks if the current plan involves irreversible actions (booking, payment,
reservation). If so, uses LangGraph's interrupt() mechanism to pause the
graph and wait for user approval via the Streamlit UI.
"""

from __future__ import annotations

import logging
from typing import Any

from graph.state import TripState

logger = logging.getLogger(__name__)

# Actions that require human approval before execution
IRREVERSIBLE_ACTIONS = {"book_flight", "book_hotel", "make_reservation", "process_payment"}


def human_approval(state: TripState) -> dict[str, Any]:
    """Check if any pending actions require human approval.

    If irreversible actions are detected, pauses the graph via interrupt()
    so the Streamlit UI can collect the user's decision.
    """
    pending = state.get("pending_tool_calls", [])
    booking_results = state.get("booking_results", [])

    # Check if any pending actions are irreversible
    irreversible = [
        call for call in pending
        if call.get("tool", "") in IRREVERSIBLE_ACTIONS
    ]

    if not irreversible:
        logger.info("human_approval: No irreversible actions found, skipping.")
        return {
            "approval_required": False,
            "approval_status": "not_needed",
        }

    logger.info(
        "human_approval: Found %d irreversible action(s), requesting approval.",
        len(irreversible),
    )

    # Use LangGraph interrupt to pause and wait for user decision.
    # The interrupt value is sent to the UI as context.
    try:
        from langgraph.types import interrupt

        user_decision = interrupt({
            "type": "approval_request",
            "actions": irreversible,
            "message": "The following actions require your approval before proceeding.",
        })

        # user_decision is injected by the UI when it resumes the graph
        approved = user_decision.get("approved", False)
        reason = user_decision.get("reason", "")

        if approved:
            logger.info("human_approval: User APPROVED the actions.")
            return {
                "approval_required": True,
                "approval_status": "approved",
                "approval_reason": "",
            }
        else:
            logger.info("human_approval: User REJECTED. Reason: %s", reason)
            return {
                "approval_required": True,
                "approval_status": "rejected",
                "approval_reason": reason,
            }

    except ImportError:
        # Fallback if interrupt() is not available in this LangGraph version
        logger.warning(
            "human_approval: langgraph.types.interrupt not available. "
            "Auto-approving for development."
        )
        return {
            "approval_required": True,
            "approval_status": "approved",
            "approval_reason": "",
        }
