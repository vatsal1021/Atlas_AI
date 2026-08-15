"""IrrelevantResponseNode — Fast conversational reply for off-topic / empty input.

Generates a short, friendly response using conversation_history context
without triggering any planning machinery.
Appends the exchange to conversation_history before routing to END.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt
from app.tracing import get_tracker

logger = logging.getLogger(__name__)


def irrelevant_response(state: TripState) -> dict[str, Any]:
    """Generate a natural conversational reply for non-travel input using history."""
    user_input = state.get("user_input", "")
    classification = state.get("intent_classification", "irrelevant")
    history = state.get("conversation_history", [])
    tracker = get_tracker()

    logger.info(
        "irrelevant_response: classification=%s  input_len=%d  history_turns=%d",
        classification, len(user_input), len(history),
    )

    system_prompt, user_template = load_prompt("irrelevant")
    user_content = user_template.format(
        user_input=user_input or "(empty message)",
        conversation_history=_format_history(history),
    )

    llm = get_llm(temperature=0.7)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    reply = response.content.strip()  # type: ignore[union-attr]

    if tracker:
        tracker.log_trace(f"[IrrelevantResponseNode] Replied to non-travel input")

    # Append exchange to conversation_history
    updated_history = list(history)
    if user_input:
        updated_history.append({"role": "user", "content": user_input})
    updated_history.append({"role": "assistant", "content": reply})

    return {
        "final_response": reply,
        "conversation_history": updated_history,
    }


def _format_history(history: list[dict]) -> str:
    """Format recent conversation history into a readable string for the prompt."""
    if not history:
        return "No prior conversation history."
    lines = []
    for msg in history[-10:]:   # Include up to last 10 messages (5 turns)
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
