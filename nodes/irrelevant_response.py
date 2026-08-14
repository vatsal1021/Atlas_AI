"""IrrelevantResponseNode — Fast conversational reply for off-topic / empty input.

Generates a short, friendly response without triggering any planning machinery.
Appends the exchange to conversation_history before routing to END.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from app.tracing import get_tracker

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are AtlasAI, a friendly travel-planning assistant. "
    "The user has sent a message that is not a travel-planning request. "
    "Reply naturally and conversationally in 1-3 sentences. "
    "If it is a greeting, greet back warmly. "
    "If it is an off-topic question, politely explain that you specialise in travel planning "
    "and invite them to share their travel plans. "
    "Do NOT attempt to plan any trip or call any tools."
)


def irrelevant_response(state: TripState) -> dict[str, Any]:
    """Generate a natural conversational reply for non-travel input."""
    user_input = state.get("user_input", "")
    classification = state.get("intent_classification", "irrelevant")
    tracker = get_tracker()

    logger.info(
        "irrelevant_response: classification=%s  input_len=%d",
        classification, len(user_input),
    )

    llm = get_llm(temperature=0.7)
    response = llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_input or "(empty message)"),
    ])

    reply = response.content.strip()  # type: ignore[union-attr]

    if tracker:
        tracker.log_trace(f"[IrrelevantResponseNode] Replied to non-travel input")

    # Append to conversation_history
    history = list(state.get("conversation_history", []))
    if user_input:
        history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})

    return {
        "final_response": reply,
        "conversation_history": history,
    }
