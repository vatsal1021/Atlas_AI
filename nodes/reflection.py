"""Reflection node logic."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt


def reflection(state: TripState) -> dict[str, Any]:
    """
    Review the current plan for critical gaps or missing information.
    If high/critical gaps are found, add them as pending tool calls to force the planner to fix them.
    """
    system_prompt, user_template = load_prompt("reflection")

    user_content = user_template.format(
        parsed_goal=json.dumps(state.get("parsed_goal", {}), indent=2),
        sub_goals=json.dumps(state.get("sub_goals", []), indent=2),
        world_facts=json.dumps(state.get("world_facts", []), indent=2),
        evidence=json.dumps(state.get("evidence", {}), indent=2),
        current_plan=json.dumps(state.get("pending_tool_calls", []), indent=2),
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
    except Exception:
        result = {"gaps": [], "overall_confidence": 1.0}

    gaps = result.get("gaps", [])
    reflection_notes = [g["description"] for g in gaps]

    # If there are high/critical gaps, create pending tool calls to force a planner loop
    new_tool_calls = []
    for gap in gaps:
        if gap.get("severity", "").lower() in ["high", "critical"]:
            new_tool_calls.append({
                "tool": "address_gap",
                "parameters": {
                    "category": gap.get("category"),
                    "description": gap.get("description"),
                    "suggested_action": gap.get("suggested_action"),
                },
                "reasoning": f"Reflection identified a critical gap: {gap.get('description')}",
                "sub_goal_id": "none",
            })

    planning_complete = len(new_tool_calls) == 0

    return {
        "reflection_gaps": gaps,
        "reflection_notes": reflection_notes,
        "pending_tool_calls": new_tool_calls,
        "planning_complete": planning_complete,
        "revision_count": state.get("revision_count", 0) + 1,
    }
