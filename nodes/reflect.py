"""ReflectNode — Evaluates whether the ReAct work is sufficient.

Checks:
  1. Objective satisfied?
  2. Constraints satisfied?
  3. Tool results valid and non-contradictory?
  4. Enough information for a high-quality response?
  5. Zero-tool plans — can we still answer well?

Outputs reflect_decision: needs_more_work | complete
If needs_more_work, writes reflect_feedback so ReactNode can adjust.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt
from app.tracing import get_tracker

logger = logging.getLogger(__name__)


def reflect(state: TripState) -> dict[str, Any]:
    """Evaluate completeness of the ReAct work and decide next step."""
    tracker = get_tracker()

    directive = state.get("planning_directive", {})
    extracted = state.get("extracted_entities", {})
    observations = state.get("tool_observations", [])
    reasoning_log = state.get("react_reasoning_log", [])
    reflect_iter = state.get("reflect_iteration", 0)
    user_input = state.get("user_input", "")

    system_prompt, user_template = load_prompt("reflect")
    user_content = user_template.format(
        user_input=user_input,
        planning_directive=json.dumps(directive, indent=2) if directive else "None",
        extracted_entities=json.dumps(extracted, indent=2),
        tool_observations=_format_observations(observations),
        react_reasoning_log="\n".join(reasoning_log[-5:]) if reasoning_log else "None",
        reflect_iteration=reflect_iter,
    )

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    result = _extract_json(str(response.content))  # type: ignore[union-attr]

    decision = result.get("decision", "complete")
    feedback = result.get("feedback", "")

    if decision not in ("needs_more_work", "complete"):
        decision = "complete"

    logger.info(
        "reflect [iter=%d]: decision=%s", reflect_iter, decision
    )
    if tracker:
        tracker.log_trace(
            f"[ReflectNode] iter={reflect_iter + 1}  decision={decision}"
        )

    return {
        "reflect_decision": decision,
        "reflect_feedback": feedback if decision == "needs_more_work" else "",
        "reflect_iteration": reflect_iter + 1,
    }


def _format_observations(observations: list[dict]) -> str:
    if not observations:
        return "No tool results (zero-tool plan)."
    lines = []
    for obs in observations:
        tool = obs.get("tool", "?")
        status = obs.get("status", "?")
        result = json.dumps(obs.get("result", {}), default=str)
        if len(result) > 400:
            result = result[:397] + "..."
        lines.append(f"  [{status.upper()}] {tool}: {result}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [l for l in cleaned.split("\n") if not l.strip().startswith("```")]
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
    return {"decision": "complete", "feedback": ""}
