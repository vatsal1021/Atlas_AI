"""AtlasAI CLI entrypoint.

Usage:
    python -m app.main "Plan me a 5-day Japan trip with a budget of 1.5 lakh INR"
    python -m app.main   # interactive prompt
"""

from __future__ import annotations

import json
import logging
import sys
import uuid

from app.config import configure_logging, get_settings
from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
from app.tracing import start_execution_tracker

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the AtlasAI travel planning agent."""
    configure_logging()
    settings = get_settings()

    # Get user input from CLI args or interactive prompt
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        print("\n🌍  AtlasAI — Autonomous Travel Planner")
        print("=" * 50)
        user_input = input("\nDescribe your trip: ").strip()
        if not user_input:
            print("No input provided. Exiting.")
            return

    # Start ExecutionTracker for full dual-file observability
    run_id = uuid.uuid4().hex[:8]
    tracker = start_execution_tracker(run_id=run_id, user_input=user_input)

    logger.info("Starting AtlasAI [Run ID: %s] with input: %s", run_id, user_input)
    print(f"\n📝 Processing: {user_input} (Run ID: {run_id})\n")

    # Build initial state
    initial_state = create_initial_state(
        user_input=user_input,
        max_iterations=settings.max_planner_iterations,
    )

    # Compile and invoke graph
    graph = compile_graph()
    config = {"configurable": {"thread_id": f"cli_{run_id}"}}
    print("🔄 Running planning loop...\n")

    try:
        final_state = graph.invoke(initial_state, config=config)
        tracker.track_workflow_complete(success=True)
        # Display results
        _print_results(final_state)
    except Exception as exc:
        tracker.track_workflow_complete(success=False, error=str(exc))
        print(f"\n❌ Execution failed: {exc}")
        raise


def _print_results(state: dict) -> None:
    """Pretty-print the final state."""
    print("\n" + "=" * 60)
    print("🎯  ATLAS AI — PLANNING RESULTS")
    print("=" * 60)

    # Parsed Goal
    parsed_goal = state.get("parsed_goal", {})
    if parsed_goal:
        print("\n📋 Parsed Goal:")
        print(f"   Destination:  {parsed_goal.get('destination', 'N/A')}")
        print(f"   Budget:       {parsed_goal.get('budget', 'N/A')} {parsed_goal.get('currency', 'INR')}")
        print(f"   Duration:     {parsed_goal.get('days', 'N/A')} days")
        print(f"   Travellers:   {parsed_goal.get('travelers', 1)}")
        prefs = parsed_goal.get("preferences", [])
        if prefs:
            print(f"   Preferences:  {', '.join(prefs)}")
        constraints = parsed_goal.get("constraints", [])
        if constraints:
            print(f"   Constraints:  {', '.join(constraints)}")

    # Sub-goals
    sub_goals = state.get("sub_goals", [])
    if sub_goals:
        print(f"\n📌 Sub-Goals ({len(sub_goals)}):")
        for sg in sub_goals:
            status_icon = "✅" if sg.get("status") == "completed" else "🔄"
            print(f"   {status_icon} [{sg.get('id')}] {sg.get('description', '')}  ({sg.get('status', 'pending')})")

    # World Facts
    world_facts = state.get("world_facts", [])
    if world_facts:
        print(f"\n🌐 World Facts ({len(world_facts)}):")
        for fact in world_facts[:10]:
            conf = fact.get("confidence", 0)
            print(f"   • [{conf:.0%}] {fact.get('statement', '')}")

    # Evaluation
    print(f"\n📊 Evaluation:")
    print(f"   Goal Satisfied:  {'✅ Yes' if state.get('goal_satisfied') else '❌ No'}")
    print(f"   Iterations:      {state.get('planner_iteration', 0)}")
    reasoning = state.get("evaluation_reasoning", "")
    if reasoning:
        print(f"   Reasoning:       {reasoning[:200]}")

    # Errors
    errors = state.get("errors", [])
    if errors:
        print(f"\n⚠️  Errors ({len(errors)}):")
        for err in errors:
            print(f"   • {err.get('error', str(err))}")

    # Planner reasoning log
    planner_reasoning = state.get("planner_reasoning", [])
    if planner_reasoning:
        print(f"\n🧠 Planner Reasoning Log:")
        for entry in planner_reasoning:
            print(f"   → {entry}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
