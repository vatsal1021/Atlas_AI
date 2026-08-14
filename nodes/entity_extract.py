"""EntityExtractNode — Structured extraction of travel entities from user input.

Merges newly extracted entities with any previously persisted entities so the
agent accumulates a complete profile across multiple negotiation turns.
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
from tools.memory import load_preferences

logger = logging.getLogger(__name__)


def entity_extract(state: TripState) -> dict[str, Any]:
    """Extract travel entities from user_input and merge with prior extracted_entities."""
    user_input = state.get("user_input", "")
    prior_entities = state.get("extracted_entities", {})
    history = state.get("conversation_history", [])
    tracker = get_tracker()

    # Load long-term user preferences on first turn
    memory_context = state.get("memory_context") or load_preferences("default")

    system_prompt, user_template = load_prompt("entity_extract")
    user_content = user_template.format(
        user_input=user_input,
        prior_entities=json.dumps(prior_entities, indent=2) if prior_entities else "None",
        conversation_history=_format_history(history),
        memory_context=json.dumps(memory_context) if memory_context else "None",
    )

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    raw = response.content  # type: ignore[union-attr]
    new_entities = _extract_json(str(raw))

    # Merge: new values override prior values for the same key
    merged = {**prior_entities, **{k: v for k, v in new_entities.items() if v not in (None, "", [], {})}}

    logger.info(
        "entity_extract: extracted_keys=%s", list(new_entities.keys())
    )
    if tracker:
        tracker.log_trace(
            f"[EntityExtractNode] Extracted: {list(new_entities.keys())}"
        )

    return {
        "extracted_entities": merged,
        "memory_context": memory_context,
    }


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from LLM output."""
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
    logger.error("entity_extract: Failed to parse JSON from LLM response")
    return {}


def _format_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history[-6:]:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")[:300]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
