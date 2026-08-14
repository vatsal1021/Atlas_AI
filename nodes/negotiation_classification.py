"""NegotiationClassificationNode — Determines if the agent has enough
information to proceed, or needs to ask a follow-up question.

Outputs negotiation_status: needs_information | information_complete
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


def negotiation_classification(state: TripState) -> dict[str, Any]:
    """Classify whether information is sufficient to proceed."""
    extracted = state.get("extracted_entities", {})
    history = state.get("conversation_history", [])
    neg_history = state.get("negotiation_history", [])
    user_input = state.get("user_input", "")
    tracker = get_tracker()

    system_prompt, user_template = load_prompt("negotiation_classification")
    user_content = user_template.format(
        user_input=user_input,
        extracted_entities=json.dumps(extracted, indent=2),
        conversation_history=_format_history(history),
        negotiation_history=json.dumps(neg_history, indent=2) if neg_history else "[]",
    )

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    result = _extract_json(str(response.content))  # type: ignore[union-attr]

    status = result.get("status", "information_complete")
    missing = result.get("missing_fields", [])
    reasoning = result.get("reasoning", "")

    # Normalise status
    if status not in ("needs_information", "information_complete"):
        status = "information_complete"

    logger.info(
        "negotiation_classification: status=%s  missing=%s", status, missing
    )
    if tracker:
        tracker.log_trace(
            f"[NegotiationClassificationNode] status={status}  missing={missing}"
        )

    return {
        "negotiation_status": status,
        "missing_fields": missing,
        "negotiation_reasoning": reasoning,
    }


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [l for l in cleaned.split("\n") if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
    return {"status": "information_complete", "missing_fields": [], "reasoning": ""}


def _format_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history[-6:]:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")[:300]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
