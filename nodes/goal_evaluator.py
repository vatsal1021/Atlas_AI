"""Goal Evaluator node.

Uses an LLM to assess which sub-goals are satisfied based on gathered
world facts and evidence.  Determines overall goal satisfaction.
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


def goal_evaluator(state: TripState) -> dict:
    """Evaluate sub-goal completion and overall satisfaction.

    Returns
    -------
    dict
        Partial state with ``goal_status``, ``goal_satisfied``,
        ``evaluation_reasoning``, and updated ``sub_goals``.
    """
    parsed_goal = state.get("parsed_goal", {})
    sub_goals = state.get("sub_goals", [])
    world_facts = state.get("world_facts", [])

    logger.info(
        "goal_evaluator  sub_goals=%d  world_facts=%d",
        len(sub_goals), len(world_facts),
    )

    system_prompt, user_template = load_prompt("evaluator")
    user_content = user_template.format(
        parsed_goal=json.dumps(parsed_goal, indent=2),
        sub_goals=json.dumps(sub_goals, indent=2),
        world_facts=json.dumps(world_facts, indent=2),
    )

    llm = get_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response = llm.invoke(messages)
    raw_content: str = response.content  # type: ignore[union-attr]
    logger.debug("goal_evaluator LLM response: %s", raw_content[:500])

    evaluation = _extract_json(raw_content)

    # Update sub-goal statuses in the sub_goals list
    sub_goal_statuses = evaluation.get("sub_goal_statuses", {})
    updated_sub_goals = []
    for sg in sub_goals:
        sg_copy = dict(sg)
        sg_id = sg.get("id", "")
        if sg_id in sub_goal_statuses:
            status_info = sub_goal_statuses[sg_id]
            if isinstance(status_info, dict) and status_info.get("satisfied", False):
                sg_copy["status"] = "completed"
            else:
                sg_copy["status"] = "in_progress"
        updated_sub_goals.append(sg_copy)

    all_satisfied = evaluation.get("all_satisfied", False)
    summary = evaluation.get("summary", "")

    logger.info("goal_evaluator  all_satisfied=%s", all_satisfied)

    return {
        "goal_status": sub_goal_statuses,
        "goal_satisfied": all_satisfied,
        "evaluation_reasoning": summary,
        "sub_goals": updated_sub_goals,
    }


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from LLM output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                pass
        logger.error("Failed to parse evaluation from LLM response")
        return {"sub_goal_statuses": {}, "all_satisfied": False, "summary": "Evaluation failed."}
