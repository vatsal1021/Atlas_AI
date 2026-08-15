"""HumanApprovalNode — Updated for new single-pending-tool-call architecture.

Reads pending_tool_call (singular dict) instead of pending_tool_calls (list).
Preserves the full interrupt() / Command(resume=...) mechanism unchanged.

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

_TOOL_ACTION_TYPE: dict[str, ActionType] = {
    "book_flight":       ActionType.BOOK_FLIGHT,
    "book_hotel":        ActionType.BOOK_HOTEL,
    "book_train":        ActionType.BOOK_TRAIN,
    "make_reservation":  ActionType.MAKE_RESERVATION,
    "process_payment":   ActionType.PROCESS_PAYMENT,
    "cancel_booking":    ActionType.OTHER,
}


def human_approval(state: TripState) -> dict[str, Any]:
    """Interrupt the graph and await human approval for an irreversible action."""
    pending = state.get("pending_tool_call", {})
    tracker = get_tracker()

    if not pending or not pending.get("tool"):
        logger.info("human_approval: no pending tool call — skipping.")
        return {
            "approval_required": False,
            "approval_status": ApprovalStatus.NOT_NEEDED.value,
        }

    # Build single ApprovalAction from the pending_tool_call dict
    tool = pending.get("tool", "")
    action = ApprovalAction(
        tool=tool,
        action_type=_TOOL_ACTION_TYPE.get(tool, ActionType.OTHER),
        parameters=pending.get("arguments", pending.get("parameters", {})),
        reasoning=pending.get("reasoning", ""),
        estimated_cost=pending.get("estimated_cost", 0.0),
        currency=state.get("extracted_entities", {}).get("currency", "INR"),
        is_reversible=False,
    )

    # Ask the LLM to compose a friendly approval message
    llm = get_llm()
    actions_summary = json.dumps(
        action.model_dump(include={"tool", "parameters", "reasoning"}), indent=2
    )
    sys_msg = SystemMessage(content=(
        "You are a travel assistant. The following irreversible action is about to be executed. "
        "Write a short, friendly confirmation message for the user (2-3 sentences) summarising "
        "what will happen and asking for approval."
    ))
    human_msg = HumanMessage(content=f"Action:\n{actions_summary}")

    try:
        response = llm.invoke([sys_msg, human_msg])
        message = response.content.strip()
    except Exception as exc:
        logger.error("human_approval: LLM failed to compose message: %s", exc)
        message = (
            "The agent is ready to execute an irreversible action. "
            "Please review and approve or reject."
        )

    approval_request = ApprovalRequest(
        type="approval_request",
        message=message,
        actions=[action],
        total_estimated_cost=action.estimated_cost,
        currency=action.currency,
    )

    logger.info("human_approval: interrupting graph for tool=%s", tool)
    if tracker:
        tracker.record_event(
            event_type="Human Approval Request",
            component="Node",
            component_name="human_approval",
            input_payload=approval_request.model_dump(),
            status="Started",
        )
        tracker.log_trace(f"[Approval] Requested for: {tool}")

    try:
        from langgraph.types import interrupt

        raw_decision = interrupt(approval_request.model_dump())

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
            tracker.log_trace(
                f"[Approval] Decision: {'Approved' if decision.approved else 'Rejected'}\n"
            )

        if decision.approved:
            logger.info("human_approval: APPROVED")
            return {
                "approval_required": True,
                "approval_status": ApprovalStatus.APPROVED.value,
                "approval_reason": "",
            }
        else:
            logger.info("human_approval: REJECTED — %s", decision.reason)
            # Log rejection in tool_observations so ReactNode can reason about it
            observations = list(state.get("tool_observations", []))
            observations.append({
                "tool": tool,
                "arguments": action.parameters,
                "result": None,
                "status": "rejected",
                "error": f"User rejected. Reason: {decision.reason}",
            })
            return {
                "approval_required": True,
                "approval_status": ApprovalStatus.REJECTED.value,
                "approval_reason": decision.reason,
                "tool_observations": observations,
                "pending_tool_call": {},
            }

    except ImportError:
        logger.warning("human_approval: interrupt not available — auto-approving.")
        return {
            "approval_required": True,
            "approval_status": ApprovalStatus.APPROVED,
            "approval_reason": "",
        }
