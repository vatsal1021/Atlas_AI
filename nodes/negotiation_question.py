"""NegotiationQuestionNode — Generates one contextual follow-up question.

Reads missing_fields and negotiation_history to produce a non-repetitive,
conversational question. Routes to END after writing final_response.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt
from app.tracing import get_tracker

logger = logging.getLogger(__name__)


def negotiation_question(state: TripState) -> dict[str, Any]:
    """Generate a follow-up question for missing travel information."""
    missing = state.get("missing_fields", [])
    neg_history = state.get("negotiation_history", [])
    history = state.get("conversation_history", [])
    user_input = state.get("user_input", "")
    extracted = state.get("extracted_entities", {})
    tracker = get_tracker()

    system_prompt, user_template = load_prompt("negotiation_question")
    user_content = user_template.format(
        user_input=user_input,
        missing_fields=json.dumps(missing),
        extracted_entities=json.dumps(extracted, indent=2),
        negotiation_history=json.dumps(neg_history, indent=2) if neg_history else "[]",
        conversation_history=_format_history(history),
    )

    llm = get_llm(temperature=0.5)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    question = response.content.strip()  # type: ignore[union-attr]

    logger.info("negotiation_question: asking for fields=%s", missing)
    if tracker:
        tracker.log_trace(
            f"[NegotiationQuestionNode] Asking about: {missing}"
        )

    # Update negotiation history
    updated_neg_history = list(neg_history) + [{"question": question, "missing_fields": missing}]

    # Append to conversation history
    conv_history = list(history)
    if user_input:
        conv_history.append({"role": "user", "content": user_input})
    conv_history.append({"role": "assistant", "content": question})

    return {
        "final_response": question,
        "negotiation_history": updated_neg_history,
        "conversation_history": conv_history,
    }


def _format_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history[-6:]:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")[:300]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
