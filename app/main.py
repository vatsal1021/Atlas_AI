"""AtlasAI CLI entrypoint with multi-turn conversation support.

Usage:
    python -m app.main "Plan me a 5-day Japan trip with a budget of 1.5 lakh INR"
    python -m app.main   # interactive multi-turn prompt
"""

from __future__ import annotations

import logging
import sys
import uuid

from app.config import configure_logging, get_settings
from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
from app.tracing import start_execution_tracker

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the AtlasAI travel planning agent in CLI mode."""
    configure_logging()

    graph = compile_graph()
    session_id = f"cli_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": session_id}}

    print("\n🌍  AtlasAI — Autonomous Travel Planning Companion")
    print("=" * 60)

    # One-shot command line argument mode
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:]).strip()
        _run_turn(user_input, graph, config, session_id)
        return

    # Interactive multi-turn loop
    print("Type your request or message. Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Good luck with your travels!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        _run_turn(user_input, graph, config, session_id)


def _run_turn(user_input: str, graph: Any, config: dict, session_id: str) -> None:
    """Execute a single graph turn preserving prior checkpoint state."""
    tracker = start_execution_tracker(run_id=session_id, user_input=user_input)

    existing_checkpoint = graph.get_state(config)
    existing_values = existing_checkpoint.values if existing_checkpoint else None
    state_input = create_initial_state(user_input, existing_state=existing_values)

    try:
        final_state = graph.invoke(state_input, config=config)
        tracker.track_workflow_complete(success=True)

        resp = final_state.get("final_response", "")
        print(f"\nAtlasAI > {resp}\n")
    except Exception as exc:
        tracker.track_workflow_complete(success=False, error=str(exc))
        print(f"\n❌ Execution error: {exc}\n")
