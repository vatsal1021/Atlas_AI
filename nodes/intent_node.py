"""IntentNode — Dual-role relevance gate and path gate.

Role A (relevance gate, entry point):
  Classifies user input as relevant | irrelevant | empty.

Role B (path gate, after NegotiationClassificationNode):
  Decides whether to plan first or execute directly.

The graph wires the same node function twice with different conditional
edges so the routing logic naturally separates the two roles.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt
from app.settings import DEFAULT_TEMPERATURE_FAST
from app.tracing import get_tracker

logger = logging.getLogger(__name__)


def intent_node(state: TripState) -> dict:
    """Classify intent or decide planning path depending on gate mode."""
    gate_mode = state.get("intent_gate_mode", "relevance")

    if gate_mode == "path":
        return _path_gate(state)
    return _relevance_gate(state)


# ---------------------------------------------------------------------------
# Role A — Relevance Gate
# ---------------------------------------------------------------------------

def _relevance_gate(state: TripState) -> dict:
    """Classify user input as relevant | irrelevant | empty."""
    user_input = state.get("user_input", "").strip()
    tracker = get_tracker()

    if not user_input:
        logger.info("intent_node [relevance]: empty input")
        if tracker:
            tracker.log_trace("[IntentNode] Empty input → irrelevant")
        return {
            "intent_classification": "empty",
            "intent_gate_mode": "relevance",
        }

    system_prompt, user_template = load_prompt("intent")
    user_content = user_template.format(
        user_input=user_input,
        conversation_history=_format_history(state.get("conversation_history", [])),
    )

    llm = get_llm(temperature=DEFAULT_TEMPERATURE_FAST)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    raw = response.content.strip().lower()  # type: ignore[union-attr]
    classification = "relevant" if "relevant" in raw else "irrelevant"
    if "irrelevant" in raw:
        classification = "irrelevant"
    if "empty" in raw:
        classification = "empty"

    logger.info("intent_node [relevance]: classification=%s", classification)
    if tracker:
        tracker.log_trace(f"[IntentNode] Relevance gate → {classification}")

    return {
        "intent_classification": classification,
        "intent_gate_mode": "relevance",
    }


# ---------------------------------------------------------------------------
# Role B — Path Gate
# ---------------------------------------------------------------------------

def _path_gate(state: TripState) -> dict:
    """Decide between 'plan' (structured directive) or 'direct_execute' (straight to ReAct)."""
    system_prompt, user_template = load_prompt("intent_path")
    user_content = user_template.format(
        extracted_entities=str(state.get("extracted_entities", {})),
        user_input=state.get("user_input", ""),
        conversation_history=_format_history(state.get("conversation_history", [])),
    )

    llm = get_llm(temperature=DEFAULT_TEMPERATURE_FAST)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])

    raw = response.content.strip().lower()  # type: ignore[union-attr]
    decision = "plan" if "plan" in raw else "direct_execute"

    tracker = get_tracker()
    logger.info("intent_node [path]: decision=%s", decision)
    if tracker:
        tracker.log_trace(f"[IntentNode] Path gate → {decision}")

    return {
        "path_decision": decision,
        "intent_gate_mode": "path",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for msg in history[-6:]:   # last 3 turns
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")[:200]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
