"""Critic node logic."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt


def critic(state: TripState) -> dict[str, Any]:
    """
    Independent critic evaluating the plan. If major flaws are found, signals to revise.
    """
    system_prompt, user_template = load_prompt("critic")

    parsed_goal = state.get("parsed_goal", {})
    budget_analysis = json.dumps({
        "budget": parsed_goal.get("budget"),
        "currency": parsed_goal.get("currency"),
    }, indent=2)

    user_content = user_template.format(
        budget_analysis=budget_analysis,
        world_facts=json.dumps(state.get("world_facts", []), indent=2),
        full_plan=json.dumps(state.get("sub_goals", []), indent=2),
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
        result = {"issues": [], "overall_rating": "good", "should_revise": False}

    issues = result.get("issues", [])
    should_revise = result.get("should_revise", False)

    # If the critic demands a revision, reset planning_complete
    planning_complete = state.get("planning_complete", True)
    if should_revise:
        planning_complete = False

    return {
        "critic_feedback": issues,
        "critic_should_revise": should_revise,
        "planning_complete": planning_complete,
        "revision_count": state.get("revision_count", 0) + 1,
    }
