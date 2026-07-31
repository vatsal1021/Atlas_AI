"""Goal Understanding node.

Parses natural-language travel requests into structured ParsedGoal objects.
Also loads returning-user preferences from memory.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import TripState
from services.llm import get_llm
from tools.memory import load_preferences

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "goal_understanding.txt"


def goal_understanding(state: TripState) -> dict:
    """Parse user input into a structured travel goal.

    Returns
    -------
    dict
        Partial state update with ``parsed_goal`` and ``memory_context``.
    """
    user_input: str = state.get("user_input", "")
    logger.info("goal_understanding  input_length=%d", len(user_input))

    # Load returning-user preferences
    memory_ctx = load_preferences("default")

    # Build prompt
    prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt_text = prompt_template.format(
        user_input=user_input,
        memory_context=json.dumps(memory_ctx) if memory_ctx else "No prior preferences.",
    )

    llm = get_llm()
    messages = [
        SystemMessage(content="You are a travel goal extraction assistant."),
        HumanMessage(content=prompt_text),
    ]

    response = llm.invoke(messages)
    raw_content: str = response.content  # type: ignore[union-attr]
    logger.debug("goal_understanding LLM response: %s", raw_content[:500])

    # Parse JSON from response (handle markdown fences)
    parsed = _extract_json(raw_content)

    return {
        "parsed_goal": parsed,
        "memory_context": memory_ctx,
    }


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from LLM output."""
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
        logger.error("Failed to parse JSON from LLM response")
        return {"error": "Failed to parse goal", "raw_response": text[:500]}
