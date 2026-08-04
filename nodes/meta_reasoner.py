"""Meta-Reasoner node.

Triggered when something fails: a tool error, a rejected approval, a
constraint violation, or the planner exceeding max iterations. Diagnoses
WHY and decides the minimal recovery action.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

# Maps recovery_strategy → target node name
RECOVERY_ROUTES: dict[str, str] = {
    "retry": "capability_dispatcher",
    "alternative": "objective_planner",
    "partial_replan": "objective_planner",
    "full_replan": "goal_decomposition",
    "escalate": "__end__",
}


def meta_reasoner(state: TripState) -> dict[str, Any]:
    """Diagnose failures and produce a recovery strategy."""
    errors = state.get("errors", [])
    failure_history = list(state.get("failure_history", []))
    recovery_attempts = state.get("recovery_attempts", 0)
    max_recovery = state.get("max_recovery_attempts", 3)

    # Build context for the LLM
    failed_component = "unknown"
    error_details = "No error details available."

    if errors:
        last_error = errors[-1]
        failed_component = last_error.get("tool", "unknown")
        error_details = last_error.get("error", "Unknown error")

    # Check for approval rejection
    if state.get("approval_status") == "rejected":
        failed_component = "human_approval"
        error_details = f"User rejected the plan. Reason: {state.get('approval_reason', 'No reason given')}"

    # Check for max iterations exceeded
    if state.get("planner_iteration", 0) >= state.get("max_iterations", 10):
        failed_component = "objective_planner"
        error_details = "Maximum planner iterations exceeded without satisfying goals."

    # If max recovery attempts exceeded, force escalation
    if recovery_attempts >= max_recovery:
        logger.warning(
            "meta_reasoner: Max recovery attempts (%d) reached. Escalating.",
            max_recovery,
        )
        failure_history.append({
            "attempt": recovery_attempts + 1,
            "failed_component": failed_component,
            "error": error_details,
            "strategy": "escalate",
            "reasoning": "Maximum recovery attempts exceeded.",
        })
        return {
            "failure_history": failure_history,
            "recovery_attempts": recovery_attempts + 1,
            "pending_tool_calls": [],
            "errors": errors,
            "explanation": {
                "escalation": True,
                "message": f"Unable to recover after {max_recovery} attempts. Last error: {error_details}",
            },
        }

    # Call LLM for diagnosis
    system_prompt, user_template = load_prompt("meta_reasoner")
    user_content = user_template.format(
        failed_component=failed_component,
        error_details=error_details,
        previous_attempts=json.dumps(failure_history, indent=2),
        state_summary=json.dumps({
            "goal_satisfied": state.get("goal_satisfied", False),
            "planner_iteration": state.get("planner_iteration", 0),
            "sub_goals_count": len(state.get("sub_goals", [])),
            "errors_count": len(errors),
            "recovery_attempts": recovery_attempts,
        }, indent=2),
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
        result = {
            "diagnosis": "Failed to parse meta-reasoner response.",
            "failed_component": failed_component,
            "recovery_strategy": "escalate",
            "actions": [],
            "reasoning": "LLM response could not be parsed.",
        }

    strategy = result.get("recovery_strategy", "escalate")
    actions = result.get("actions", [])

    logger.info(
        "meta_reasoner: strategy=%s  diagnosis=%s",
        strategy, result.get("diagnosis", ""),
    )

    # Record this recovery attempt
    failure_history.append({
        "attempt": recovery_attempts + 1,
        "failed_component": failed_component,
        "error": error_details,
        "strategy": strategy,
        "reasoning": result.get("reasoning", ""),
    })

    # Build recovery actions as pending tool calls
    recovery_tool_calls = []
    for action in actions:
        recovery_tool_calls.append({
            "tool": action.get("tool", ""),
            "parameters": action.get("parameters", {}),
            "reasoning": action.get("reasoning", ""),
            "sub_goal_id": "recovery",
        })

    return {
        "failure_history": failure_history,
        "recovery_attempts": recovery_attempts + 1,
        "pending_tool_calls": recovery_tool_calls,
        "errors": [],  # Clear errors after handling
    }
