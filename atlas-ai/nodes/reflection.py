"""Reflection node logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "reflection.txt"


def reflection(state: TripState) -> dict[str, Any]:
    """
    Review the current plan for critical gaps or missing information.
    If high/critical gaps are found, add them as pending tool calls to force the planner to fix them.
    """
    prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    
    # Format state for injection
    parsed_goal = json.dumps(state.get("parsed_goal", {}), indent=2)
    sub_goals = json.dumps(state.get("sub_goals", []), indent=2)
    world_facts = json.dumps(state.get("world_facts", []), indent=2)
    evidence = json.dumps(state.get("evidence", {}), indent=2)
    current_plan = json.dumps(state.get("pending_tool_calls", []), indent=2)

    prompt = prompt_template.format(
        parsed_goal=parsed_goal,
        sub_goals=sub_goals,
        world_facts=world_facts,
        evidence=evidence,
        current_plan=current_plan
    )

    llm = get_llm(json_mode=True)
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Evaluate the current plan for critical gaps.")
    ]

    response = llm.invoke(messages)
    
    try:
        content = str(response.content)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        result = json.loads(content)
    except Exception as e:
        # Fallback empty
        result = {"gaps": [], "overall_confidence": 1.0}
        
    gaps = result.get("gaps", [])
    reflection_notes = [g["description"] for g in gaps]
    
    # If there are high/critical gaps, create pending tool calls to force a planner loop
    new_tool_calls = []
    for gap in gaps:
        if gap.get("severity", "").lower() in ["high", "critical"]:
            # We inject a pseudo-tool call that instructs the planner to fix this gap
            new_tool_calls.append({
                "tool": "address_gap",
                "parameters": {
                    "category": gap.get("category"),
                    "description": gap.get("description"),
                    "suggested_action": gap.get("suggested_action")
                },
                "reasoning": f"Reflection identified a critical gap: {gap.get('description')}",
                "sub_goal_id": "none"  # This is a global fix
            })
            
    # Also we want to ensure the planner loop runs again if we added tool calls
    planning_complete = len(new_tool_calls) == 0

    return {
        "reflection_gaps": gaps,
        "reflection_notes": reflection_notes,
        "pending_tool_calls": new_tool_calls,
        "planning_complete": planning_complete,
        "revision_count": state.get("revision_count", 0) + 1
    }
