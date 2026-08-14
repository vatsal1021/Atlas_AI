"""Human Approval node.

Checks if the current plan involves irreversible actions (booking, payment,
reservation) using an LLM to dynamically determine whether approval is needed.
If so, uses LangGraph's interrupt() mechanism to pause the graph and wait for
user approval via the Streamlit UI.

Schemas: schemas.approval_schema.ApprovalRequest / ApprovalResponse
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage
from services.llm import get_llm
from graph.state import TripState
from schemas.approval_schema import (
    ApprovalAction,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    ActionType,
)
from app.tracing import get_tracker

logger = logging.getLogger(__name__)

# Tools that always require approval
_IRREVERSIBLE_TOOLS: set[str] = {
    "book_flight",
    "book_hotel",
    "make_reservation",
    "process_payment",
}

# Map tool name → ActionType
_TOOL_ACTION_TYPE: dict[str, ActionType] = {
    "book_flight": ActionType.BOOK_FLIGHT,
    "book_hotel": ActionType.BOOK_HOTEL,
    "make_reservation": ActionType.MAKE_RESERVATION,
    "process_payment": ActionType.PROCESS_PAYMENT,
}


def _build_approval_actions(pending: list[dict]) -> list[ApprovalAction]:
    """Convert raw pending tool call dicts to validated ApprovalAction models."""
    actions = []
    for call in pending:
        tool = call.get("tool", "")
        if tool not in _IRREVERSIBLE_TOOLS:
            continue
        actions.append(
            ApprovalAction(
                tool=tool,
                action_type=_TOOL_ACTION_TYPE.get(tool, ActionType.OTHER),
                parameters=call.get("parameters", {}),
                reasoning=call.get("reasoning", ""),
                sub_goal_id=call.get("sub_goal_id", ""),
                estimated_cost=call.get("estimated_cost", 0.0),
                currency=call.get("currency", "INR"),
                is_reversible=False,
            )
        )
    return actions


def human_approval(state: TripState) -> dict[str, Any]:
    """Check if any pending actions require human approval, then interrupt if so."""
    pending = state.get("pending_tool_calls", [])

    if not pending:
        logger.info("human_approval: No pending actions, skipping.")
        return {
            "approval_required": False,
            "approval_status": ApprovalStatus.NOT_NEEDED,
        }

    irreversible_actions = _build_approval_actions(pending)

    if not irreversible_actions:
        logger.info("human_approval: No irreversible actions found, skipping.")
        return {
            "approval_required": False,
            "approval_status": ApprovalStatus.NOT_NEEDED,
        }

    # Ask the LLM to compose a friendly approval message
    llm = get_llm()
    actions_summary = json.dumps(
        [a.model_dump(include={"tool", "parameters", "reasoning"}) for a in irreversible_actions],
        indent=2,
    )
    sys_msg = SystemMessage(content=(
        "You are a travel assistant. The following irreversible actions are about to be executed. "
        "Write a short, friendly confirmation message for the user summarising what will happen "
        "and asking for approval. Be concise (2-3 sentences)."
    ))
    human_msg = HumanMessage(content=f"Actions:\n{actions_summary}")

    try:
        response = llm.invoke([sys_msg, human_msg])
        message = response.content.strip()
    except Exception as exc:
        logger.error("human_approval: LLM failed to compose message: %s", exc)
        message = (
            "The agent is ready to execute the following irreversible actions. "
            "Please review and approve or reject."
        )

    # Build a fully-typed ApprovalRequest to pass to the UI
    total_cost = sum(a.estimated_cost for a in irreversible_actions)
    approval_request = ApprovalRequest(
        type="approval_request",
        message=message,
        actions=irreversible_actions,
        total_estimated_cost=total_cost,
        currency=state.get("parsed_goal", {}).get("currency", "INR"),
    )

    logger.info(
        "human_approval: %d irreversible action(s) pending. Interrupting graph.",
        len(irreversible_actions),
    )

    tracker = get_tracker()
    if tracker:
        tracker.record_event(
            event_type="Human Approval Request",
            component="Node",
            component_name="human_approval",
            input_payload=approval_request.model_dump(),
            status="Started",
        )
        tracker.log_trace(f"[Approval] Requested for {len(irreversible_actions)} action(s)")

    # Interrupt the graph — LangGraph pauses here until the UI resumes
    try:
        from langgraph.types import interrupt

        raw_decision = interrupt(approval_request.model_dump())

        # Validate the resume payload
        try:
            decision = ApprovalResponse.model_validate(raw_decision)
        except Exception:
            decision = ApprovalResponse(
                approved=bool(raw_decision.get("approved", False)),
                reason=str(raw_decision.get("reason", "")),
            )

        if tracker:
            tracker.record_event(
                event_type="Human Approval Response",
                component="Node",
                component_name="human_approval",
                output_response=decision.model_dump(),
                status="Approved" if decision.approved else "Rejected",
            )
            tracker.log_trace(f"[Approval] User decision: {'Approved' if decision.approved else 'Rejected'}\n")

        if decision.approved:
            logger.info("human_approval: User APPROVED.")
            return {
                "approval_required": True,
                "approval_status": ApprovalStatus.APPROVED,
                "approval_reason": "",
            }
        else:
            logger.info("human_approval: User REJECTED. Reason: %s", decision.reason)
            return {
                "approval_required": True,
                "approval_status": ApprovalStatus.REJECTED,
                "approval_reason": decision.reason,
            }

    except ImportError:
        logger.warning(
            "human_approval: langgraph.types.interrupt not available. "
            "Auto-approving for development."
        )
        return {
            "approval_required": True,
            "approval_status": ApprovalStatus.APPROVED,
            "approval_reason": "",
        }
