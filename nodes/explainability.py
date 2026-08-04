"""Explainability node logic."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt


def explainability(state: TripState) -> dict[str, Any]:
    """
    Generate a human-readable explanation of the final plan, including tradeoffs and risks.
    """
    system_prompt, user_template = load_prompt("explainability")

    user_content = user_template.format(
        world_facts=json.dumps(state.get("world_facts", []), indent=2),
        final_plan=json.dumps(state.get("sub_goals", []), indent=2),
        reflection_notes=json.dumps(state.get("reflection_notes", []), indent=2),
        critic_feedback=json.dumps(state.get("critic_feedback", []), indent=2),
    )

    llm = get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response = llm.invoke(messages)

    try:
        content = str(response.content)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        result = json.loads(content)
        explanation = result.get("explanation", result)
    except Exception:
        explanation = {"error": "Failed to generate explanation."}

    return {"explanation": explanation}
