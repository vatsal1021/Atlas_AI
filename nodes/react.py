"""ReactNode — The central ReAct (Reason + Act) engine.

On each invocation it reads the full context (directive, entities, tool
observations, reflect feedback) and decides ONE of:
  - act            → select a non-critical tool
  - critical_action → select an irreversible tool (triggers HumanApprovalNode)
  - respond        → enough work done, proceed to ReflectNode
  - complete       → same as respond, used when max iterations guard fires

Tool ordering is fully dynamic — determined by LLM reasoning each step.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt
from app.settings import IRREVERSIBLE_TOOLS
from app.tracing import get_tracker
from graph.tool_selection_memory import ToolSelectionMemory

logger = logging.getLogger(__name__)


def react(state: TripState) -> dict[str, Any]:
    """Reason over context and decide next action or conclusion."""
    tracker = get_tracker()

    directive = state.get("planning_directive", {})
    extracted = state.get("extracted_entities", {})
    observations = state.get("tool_observations", [])
    reasoning_log = list(state.get("react_reasoning_log", []))
    reflect_feedback = state.get("reflect_feedback", "")
    history = state.get("conversation_history", [])
    user_input = state.get("user_input", "")
    react_iter = state.get("react_iteration", 0)

    # Build tool selection memory context
    tsm = ToolSelectionMemory(state.get("tool_selection_memory", {}))

    system_prompt, user_template = load_prompt("react")
    user_content = user_template.format(
        user_input=user_input,
        planning_directive=json.dumps(directive, indent=2) if directive else "None",
        extracted_entities=json.dumps(extracted, indent=2),
        tool_observations=_format_observations(observations),
        reflect_feedback=reflect_feedback or "None",
        tool_memory_summary=tsm.summary(),
        conversation_history=_format_history(history),
        react_iteration=react_iter,
    )

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    result = _extract_json(str(response.content))  # type: ignore[union-attr]

    decision = result.get("decision", "respond")
    reasoning = result.get("reasoning", "")
    tool_call = result.get("tool_call", {})

    # Normalise decision
    if decision not in ("act", "critical_action", "respond", "complete"):
        decision = "respond"

    # Determine if this tool is irreversible
    tool_name = tool_call.get("tool", "") if tool_call else ""
    if decision == "act" and tool_name in IRREVERSIBLE_TOOLS:
        decision = "critical_action"

    reasoning_log.append(f"[Step {react_iter + 1}] {reasoning}")

    logger.info(
        "react [iter=%d]: decision=%s  tool=%s",
        react_iter, decision, tool_name or "none",
    )
    if tracker:
        tracker.log_trace(
            f"[ReactNode] iter={react_iter + 1}  decision={decision}"
            + (f"  tool={tool_name}" if tool_name else "")
        )

    update: dict[str, Any] = {
        "react_decision": decision,
        "react_reasoning_log": reasoning_log,
        "react_iteration": react_iter + 1,
        "requires_approval": decision == "critical_action",
    }

    if decision in ("act", "critical_action") and tool_call:
        update["pending_tool_call"] = tool_call
    else:
        update["pending_tool_call"] = {}

    return update


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_observations(observations: list[dict]) -> str:
    if not observations:
        return "No tool results yet."
    lines = []
    for obs in observations:
        tool = obs.get("tool", "?")
        status = obs.get("status", "?")
        result = json.dumps(obs.get("result", {}), default=str)
        if len(result) > 400:
            result = result[:397] + "..."
        lines.append(f"  [{status.upper()}] {tool}: {result}")
    return "\n".join(lines)


def _format_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history[-4:]:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")[:200]
        lines.append(f"{role}: {content}")
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
    return {"decision": "respond", "reasoning": "Could not parse LLM response.", "tool_call": {}}
