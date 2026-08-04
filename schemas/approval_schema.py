"""Pydantic schemas for the human-in-the-loop approval flow (Phase 3).

These models validate and serialise the data passed between the
human_approval node, the Streamlit UI, and the action_dispatcher node.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ApprovalStatus(str, Enum):
    """Possible states of an approval gate."""

    NOT_NEEDED = "not_needed"   # No irreversible actions were pending
    PENDING = "pending"         # Awaiting user decision (interrupt active)
    APPROVED = "approved"       # User confirmed execution
    REJECTED = "rejected"       # User declined; hand off to meta-reasoner


class ActionType(str, Enum):
    """Types of actions that may require approval."""

    BOOK_FLIGHT = "book_flight"
    BOOK_HOTEL = "book_hotel"
    MAKE_RESERVATION = "make_reservation"
    PROCESS_PAYMENT = "process_payment"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Approval request / response
# ---------------------------------------------------------------------------


class ApprovalAction(BaseModel):
    """A single action item presented to the user for review."""

    tool: str = Field(description="The tool function that would be invoked")
    action_type: ActionType = Field(
        default=ActionType.OTHER,
        description="Categorised action type for UI rendering",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments that will be passed to the tool",
    )
    reasoning: str = Field(
        default="",
        description="Why the agent wants to perform this action",
    )
    sub_goal_id: str = Field(
        default="",
        description="Which sub-goal this action satisfies",
    )
    estimated_cost: float = Field(
        default=0.0,
        description="Estimated cost of this action (INR or stated currency)",
    )
    currency: str = Field(default="INR")
    is_reversible: bool = Field(
        default=False,
        description="Whether this action can be undone after execution",
    )
    cancellation_policy: str = Field(
        default="",
        description="Summary of the cancellation / reversal terms",
    )


class ApprovalRequest(BaseModel):
    """The payload sent to the Streamlit UI when the graph is interrupted.

    This is the value returned by ``langgraph.types.interrupt()``.
    """

    type: str = Field(default="approval_request", description="Event type tag")
    message: str = Field(
        description=(
            "Human-readable summary the agent produces "
            "(e.g. 'I've found a flight + hotel within budget. Approve?')"
        )
    )
    actions: list[ApprovalAction] = Field(
        default_factory=list,
        description="Ordered list of actions requiring approval",
    )
    total_estimated_cost: float = Field(
        default=0.0,
        description="Sum of all action costs in the stated currency",
    )
    currency: str = Field(default="INR")
    risks: list[str] = Field(
        default_factory=list,
        description="Known risks or caveats the user should be aware of",
    )


class ApprovalResponse(BaseModel):
    """The payload the Streamlit UI injects back into the graph via ``Command(resume=…)``.

    The ``human_approval`` node reads this to decide the next step.
    """

    approved: bool = Field(description="True if the user approved all actions")
    reason: str = Field(
        default="",
        description="Free-text rejection reason (only meaningful when approved=False)",
    )
    partial_approval: list[str] = Field(
        default_factory=list,
        description=(
            "If the user selectively approved only some tools, "
            "list their names here. Empty means all-or-nothing."
        ),
    )


# ---------------------------------------------------------------------------
# Booking & payment confirmation schemas (outputs of action_dispatcher)
# ---------------------------------------------------------------------------


class BookingConfirmation(BaseModel):
    """Returned by book_flight / book_hotel after a successful booking."""

    booking_id: str = Field(description="Unique booking reference")
    type: str = Field(description="flight | hotel")
    status: str = Field(default="confirmed", description="confirmed | failed | pending")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw details of what was booked",
    )
    cancellation_policy: str = Field(default="")
    booked_at: str = Field(default="", description="ISO timestamp of booking")
    is_stub: bool = Field(
        default=True,
        description="True while the real booking API is not connected",
    )


class ReservationConfirmation(BaseModel):
    """Returned by make_reservation after a successful reservation."""

    reservation_id: str = Field(description="Unique reservation reference")
    type: str = Field(default="reservation")
    status: str = Field(default="confirmed")
    activity: str = Field(default="")
    date: str = Field(default="")
    participants: int = Field(default=1)
    details: dict[str, Any] = Field(default_factory=dict)
    cancellation_policy: str = Field(default="")
    reserved_at: str = Field(default="")
    is_stub: bool = Field(default=True)


class PaymentReceipt(BaseModel):
    """Returned by process_payment after a successful charge."""

    transaction_id: str = Field(description="Unique transaction reference")
    type: str = Field(default="payment")
    status: str = Field(default="completed", description="completed | failed | refunded")
    amount: float = Field(description="Amount charged")
    currency: str = Field(default="INR")
    method: str = Field(default="credit_card", description="Payment method used")
    details: dict[str, Any] = Field(default_factory=dict)
    processed_at: str = Field(default="", description="ISO timestamp of processing")
    is_stub: bool = Field(default=True)
