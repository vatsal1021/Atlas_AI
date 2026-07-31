"""Explainability node logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "explainability.txt"


def explainability(state: TripState) -> dict[str, Any]:
    """
    Generate a human-readable explanation of the final plan, including tradeoffs and risks.
    """
    prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    
    world_facts = json.dumps(state.get("world_facts", []), indent=2)
    final_plan = json.dumps(state.get("sub_goals", []), indent=2)
    reflection_notes = json.dumps(state.get("reflection_notes", []), indent=2)
    critic_feedback = json.dumps(state.get("critic_feedback", []), indent=2)

    prompt = prompt_template.format(
        world_facts=world_facts,
        final_plan=final_plan,
        reflection_notes=reflection_notes,
        critic_feedback=critic_feedback
    )

    llm = get_llm(json_mode=True)
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Generate a structured explanation for the final travel plan.")
    ]

    response = llm.invoke(messages)
    
    try:
        content = str(response.content)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        result = json.loads(content)
        explanation = result.get("explanation", result) # Handle nested or flat structure
    except Exception as e:
        explanation = {"error": "Failed to generate explanation."}

    return {
        "explanation": explanation
    }
