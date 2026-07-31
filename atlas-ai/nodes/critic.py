"""Critic node logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "critic.txt"


def critic(state: TripState) -> dict[str, Any]:
    """
    Independent critic evaluating the plan. If major flaws are found, signals to revise.
    """
    prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    
    # Format state for injection
    parsed_goal = state.get("parsed_goal", {})
    budget_analysis = json.dumps({
        "budget": parsed_goal.get("budget"),
        "currency": parsed_goal.get("currency")
    }, indent=2)
    world_facts = json.dumps(state.get("world_facts", []), indent=2)
    full_plan = json.dumps(state.get("sub_goals", []), indent=2)

    prompt = prompt_template.format(
        budget_analysis=budget_analysis,
        world_facts=world_facts,
        full_plan=full_plan
    )

    llm = get_llm(json_mode=True)
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Critique the proposed travel plan strictly.")
    ]

    response = llm.invoke(messages)
    
    try:
        content = str(response.content)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        result = json.loads(content)
    except Exception as e:
        result = {"issues": [], "overall_rating": "good", "should_revise": False}
        
    issues = result.get("issues", [])
    should_revise = result.get("should_revise", False)
    
    # If the critic demands a revision, we reset planning_complete to False
    planning_complete = state.get("planning_complete", True)
    if should_revise:
        planning_complete = False

    return {
        "critic_feedback": issues,
        "critic_should_revise": should_revise,
        "planning_complete": planning_complete,
        "revision_count": state.get("revision_count", 0) + 1
    }
