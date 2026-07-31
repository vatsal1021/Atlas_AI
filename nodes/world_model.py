"""World Model node.

Uses an LLM to convert raw evidence into human-readable world facts with
confidence scores and implications.  Accumulates facts across iterations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import TripState
from services.llm import get_llm

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "world_model.txt"


def world_model(state: TripState) -> dict:
    """Derive world facts from raw evidence.

    Returns
    -------
    dict
        Partial state with updated ``world_facts``.
    """
    evidence = state.get("evidence", {})
    existing_facts = list(state.get("world_facts", []))

    if not evidence:
        logger.info("world_model  no evidence to process")
        return {"world_facts": existing_facts}

    # Compute next fact ID
    next_id = len(existing_facts) + 1

    logger.info(
        "world_model  evidence_categories=%s  existing_facts=%d",
        list(evidence.keys()), len(existing_facts),
    )

    prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt_text = prompt_template.format(
        evidence=json.dumps(evidence, indent=2),
        next_fact_id=next_id,
    )

    llm = get_llm()
    messages = [
        SystemMessage(content="You are a world-model builder for a travel planning agent."),
        HumanMessage(content=prompt_text),
    ]

    response = llm.invoke(messages)
    raw_content: str = response.content  # type: ignore[union-attr]
    logger.debug("world_model LLM response: %s", raw_content[:500])

    new_facts = _extract_json_list(raw_content)

    # Deduplicate by fact ID
    existing_ids = {f.get("id") for f in existing_facts}
    for fact in new_facts:
        if fact.get("id") not in existing_ids:
            existing_facts.append(fact)
            existing_ids.add(fact.get("id"))

    logger.info("world_model  total_facts=%d  new=%d", len(existing_facts), len(new_facts))
    return {"world_facts": existing_facts}


def _extract_json_list(text: str) -> list[dict]:
    """Best-effort JSON list extraction from LLM output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
        return [result]
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
        logger.error("Failed to parse world facts from LLM response")
        return []
