"""EntityExtractNode — Structured extraction of travel entities from user input.

Merges newly extracted entities with any previously persisted entities so the
agent accumulates a complete profile across multiple negotiation turns.
"""

from __future__ import annotations

import json
import logging
import re
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

    # Preserve day component when partial month/year corrections are made
    if "start_date" in prior_entities and "start_date" in new_entities:
        merged["start_date"] = _merge_date_entities(prior_entities["start_date"], new_entities["start_date"], history)

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


def _merge_date_entities(prior_date: Any, new_date: Any, history: list[dict]) -> Any:
    """Intelligently merge date components so partial updates (e.g. 'august 2026')
    don't drop previously stated days (e.g. '20th').
    """
    p_str = str(prior_date or "")
    n_str = str(new_date or "")

    if not n_str and not p_str:
        return None
    if not p_str:
        return n_str
    if not n_str:
        return p_str

    # Extract day from prior_date or history if missing in new_date
    day_match_new = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])\b', n_str)
    day_match_prior = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])\b', p_str)

    if not day_match_prior and history:
        for msg in reversed(history):
            content = msg.get("content", "")
            d_m = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?\b', content, re.IGNORECASE)
            if d_m:
                day_match_prior = d_m
                break

    # Check if prior had a day but new does not
    if not day_match_new and day_match_prior:
        day = day_match_prior.group(1).zfill(2)
        year_match = re.search(r'\b(20[2-9][0-9])\b', n_str)
        month_match = re.search(r'\b(0?[1-9]|1[0-2])\b', n_str)
        
        months_map = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
            "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
        }
        found_month = None
        for m_name, m_code in months_map.items():
            if m_name in n_str.lower():
                found_month = m_code
                break
        
        if not found_month and month_match:
            found_month = month_match.group(1).zfill(2)

        found_year = year_match.group(1) if year_match else None

        if found_month and found_year:
            return f"{found_year}-{found_month}-{day}"

    return n_str


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
