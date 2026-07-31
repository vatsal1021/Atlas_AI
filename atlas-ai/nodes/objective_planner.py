"""Objective Planner node — the brain of the agent.

Reasons about current state and decides the next best actions to take.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import TripState
from services.llm import get_llm

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "planner.txt"


def objective_planner(state: TripState) -> dict:
    """Decide the next set of tool calls based on current state.

    Returns
    -------
    dict
        Partial state with ``pending_tool_calls``, ``planner_reasoning``,
        ``planner_iteration``, and optionally ``planning_complete``.
    """
    parsed_goal = state.get("parsed_goal", {})
    sub_goals = state.get("sub_goals", [])
    world_facts = state.get("world_facts", [])
    evidence = state.get("evidence", {})
    errors = state.get("errors", [])
    iteration = state.get("planner_iteration", 0)
    prev_reasoning = state.get("planner_reasoning", [])

    logger.info(
        "objective_planner  iteration=%d  sub_goals=%d  facts=%d",
        iteration, len(sub_goals), len(world_facts),
    )

    prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt_text = prompt_template.format(
        parsed_goal=json.dumps(parsed_goal, indent=2),
        sub_goals=json.dumps(sub_goals, indent=2),
        world_facts=json.dumps(world_facts, indent=2),
        evidence=json.dumps(evidence, indent=2) if evidence else "None yet.",
        errors=json.dumps(errors, indent=2) if errors else "None.",
        planner_iteration=iteration,
    )

    llm = get_llm()
    messages = [
        SystemMessage(content="You are the planning brain of an autonomous travel agent."),
        HumanMessage(content=prompt_text),
    ]

    response = llm.invoke(messages)
    raw_content: str = response.content  # type: ignore[union-attr]
    logger.debug("objective_planner LLM response: %s", raw_content[:500])

    actions = _extract_json_list(raw_content)
    planning_complete = len(actions) == 0

    reasoning_entry = (
        f"Iteration {iteration + 1}: "
        + (f"Planned {len(actions)} action(s)." if actions else "All goals appear satisfied — no further actions.")
    )

    return {
        "pending_tool_calls": actions,
        "planner_reasoning": prev_reasoning + [reasoning_entry],
        "planner_iteration": iteration + 1,
        "planning_complete": planning_complete,
    }


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
        logger.error("Failed to parse planner actions from LLM response")
        return []
