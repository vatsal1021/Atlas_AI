"""Test case: Book a flight ticket from Lucknow to Delhi on 20 August."""
import sys
sys.path.insert(0, ".")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state

graph = compile_graph()
config = {"configurable": {"thread_id": "test_flight_booking_001"}}

user_msg = "book a flight ticket from lucknow to delhi on 20 august"
print(f"=== USER INPUT: '{user_msg}' ===")

state = create_initial_state(user_msg)

# Run graph until interrupt or END
events = []
for evt in graph.stream(state, config=config):
    for node, upd in evt.items():
        events.append(node)
        print(f"  [NODE] {node}")
        if "react_decision" in upd:
            print(f"    -> react_decision: {upd.get('react_decision')}")
        if "pending_tool_call" in upd and upd["pending_tool_call"]:
            print(f"    -> pending_tool_call: {upd['pending_tool_call']}")

current_state = graph.get_state(config)
print("\n--- Graph State after Pass 1 ---")
print(f"Next nodes in queue: {current_state.next}")

if current_state.tasks and any(t.interrupts for t in current_state.tasks):
    print("\n>>> GRAPH INTERRUPTED FOR HUMAN APPROVAL <<<")
    for task in current_state.tasks:
        if task.interrupts:
            print(f"Approval Request Message: {task.interrupts[0].value.get('message')}")
            print(f"Approval Actions: {task.interrupts[0].value.get('actions')}")

    # Resume graph with Approval APPROVED
    from langgraph.types import Command
    print("\n=== RESUMING WITH APPROVAL (approved=True) ===")
    resume_cmd = Command(resume={"approved": True, "reason": "User approved booking"})
    
    for evt in graph.stream(resume_cmd, config=config):
        for node, upd in evt.items():
            print(f"  [RESUME NODE] {node}")

final_state = graph.get_state(config).values
print("\n=== FINAL STATE SUMMARY ===")
print(f"Intent: {final_state.get('intent_classification')}")
print(f"Extracted Entities: {final_state.get('extracted_entities')}")
print(f"Booking Results: {final_state.get('booking_results')}")
print(f"Final Response ({len(final_state.get('final_response', ''))} chars):\n")
print(final_state.get("final_response"))
