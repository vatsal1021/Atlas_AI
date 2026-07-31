"""Human Approval node.

Checks if the current plan involves irreversible actions (booking, payment,
reservation) using an LLM to dynamically determine if approval is needed.
If so, uses LangGraph's interrupt() mechanism to pause the
graph and wait for user approval via the Streamlit UI.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage
from services.llm import get_llm
from graph.state import TripState

logger = logging.getLogger(__name__)


def human_approval(state: TripState) -> dict[str, Any]:
    """Check if any pending actions require human approval dynamically via LLM.

    If irreversible actions are detected, pauses the graph via interrupt()
    so the Streamlit UI can collect the user's decision.
    """
    pending = state.get("pending_tool_calls", [])
    
    if not pending:
        logger.info("human_approval: No pending actions, skipping.")
        return {
            "approval_required": False,
            "approval_status": "not_needed",
        }

    llm = get_llm()
    sys_msg = SystemMessage(content=(
        "You are a helpful travel assistant. You are about to execute a set of actions (tools). "
        "Review these actions and determine if human approval is required. "
        "Irreversible actions like bookings, reservations, or payments ALWAYS require approval. "
        "Return a JSON object exactly like this: "
        '{"requires_approval": true/false, "message": "A friendly message asking the user for permission, if needed"}. '
        "If approval is needed, the message should briefly summarize what you are doing "
        "(e.g., 'I have found the following itinerary... Would you like me to book it? (Yes/No)'). "
        "If no approval is needed, set requires_approval to false and leave the message empty."
    ))
    
    human_msg = HumanMessage(content=f"Pending actions: {json.dumps(pending, indent=2)}\n\nCurrent Plan:\n{json.dumps(state.get('parsed_goal', {}))}")
    
    logger.info("human_approval: Consulting LLM for approval requirement...")
    try:
        response = llm.invoke([sys_msg, human_msg])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        result = json.loads(content)
        requires_approval = result.get("requires_approval", False)
        message = result.get("message", "The following actions require your approval.")
        
    except Exception as e:
        logger.error(f"Failed to parse LLM approval decision: {e}")
        # Fallback to simple keyword check if LLM fails
        irreversible = [
            c for c in pending 
            if "book" in c.get("tool", "").lower() or "payment" in c.get("tool", "").lower() or "reserv" in c.get("tool", "").lower()
        ]
        requires_approval = len(irreversible) > 0
        message = "The following actions require your approval before proceeding."

    if not requires_approval:
        logger.info("human_approval: LLM decided no approval is needed.")
        return {
            "approval_required": False,
            "approval_status": "not_needed",
        }

    logger.info("human_approval: Approval required. Message: %s", message)

    # Use LangGraph interrupt to pause and wait for user decision.
    # The interrupt value is sent to the UI as context.
    try:
        from langgraph.types import interrupt

        user_decision = interrupt({
            "type": "approval_request",
            "actions": pending,
            "message": message,
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
