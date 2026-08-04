"""Goal Decomposition node.

Takes a parsed goal and decomposes it into categorised, prioritised sub-goals.
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


def goal_decomposition(state: TripState) -> dict:
    """Decompose the parsed goal into sub-goals.

    Returns
    -------
    dict
        Partial state update with ``sub_goals``.
    """
    parsed_goal = state.get("parsed_goal", {})
    logger.info("goal_decomposition  destination=%s", parsed_goal.get("destination", "?"))

    system_prompt, user_template = load_prompt("goal_decomposition")
    user_content = user_template.format(
        parsed_goal=json.dumps(parsed_goal, indent=2),
    )

    llm = get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response = llm.invoke(messages)
    raw_content: str = response.content  # type: ignore[union-attr]
    logger.debug("goal_decomposition LLM response: %s", raw_content[:500])

    sub_goals = _extract_json_list(raw_content)

    return {"sub_goals": sub_goals}


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
        logger.error("Failed to parse sub-goals from LLM response")
        return []
