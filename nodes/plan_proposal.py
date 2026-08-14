"""PlanProposalDirectiveNode — Creates a structured planning directive for ReactNode.

Does NOT execute any tools. Produces a thinking/structuring artefact that
ReactNode uses as its guiding objective for the entire ReAct loop.

Also writes a multi_agent_hint stub for future multi-agent collaboration.
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


def plan_proposal(state: TripState) -> dict[str, Any]:
    """Produce a structured planning directive and route to ReactNode."""
    extracted = state.get("extracted_entities", {})
    history = state.get("conversation_history", [])
    user_input = state.get("user_input", "")
    tracker = get_tracker()

    system_prompt, user_template = load_prompt("plan_proposal")
    user_content = user_template.format(
        user_input=user_input,
        extracted_entities=json.dumps(extracted, indent=2),
        conversation_history=_format_history(history),
    )

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    directive = _extract_json(str(response.content))  # type: ignore[union-attr]

    # Ensure required keys exist with sensible defaults
    directive.setdefault("objective", user_input)
    directive.setdefault("constraints", [])
    directive.setdefault("required_decisions", [])
    directive.setdefault("success_criteria", [])
    directive.setdefault("known_assumptions", [])

    # Multi-agent hint — extension point for future specialised agents
    multi_agent_hint = _build_multi_agent_hint(directive, extracted)

    logger.info(
        "plan_proposal: objective=%s  decisions=%d",
        directive.get("objective", "")[:80],
        len(directive.get("required_decisions", [])),
    )
    if tracker:
        tracker.log_trace(
            f"[PlanProposalDirectiveNode] Objective: {directive.get('objective', '')[:100]}"
        )

    return {
        "planning_directive": directive,
        "multi_agent_hint": multi_agent_hint,
        # Reset ReAct counters for this pass
        "react_iteration": 0,
        "tool_observations": state.get("tool_observations", []),
        "react_reasoning_log": [],
    }


def _build_multi_agent_hint(directive: dict, entities: dict) -> dict:
    """Placeholder multi-agent routing hint (not yet executed)."""
    hints = []
    if "budget" in entities or "budget" in str(directive.get("constraints", [])).lower():
        hints.append("Budget Agent")
    if entities.get("destination"):
        hints.append("Local Expert")
    if any(
        kw in str(directive.get("required_decisions", [])).lower()
        for kw in ["book", "flight", "hotel", "reservation"]
    ):
        hints.append("Booking Specialist")
    hints.append("Travel Planner")
    return {"suggested_agents": hints, "enabled": False}


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
    return {}


def _format_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history[-6:]:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")[:300]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
