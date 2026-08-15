"""Integration test for train search and train booking workflow."""
import sys
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state

graph = compile_graph()
config = {"configurable": {"thread_id": "test_train_booking_001"}}

user_msg = "book the train ticket from kanpur to delhi on 20 august"
print(f"=== USER INPUT: '{user_msg}' ===")

state = create_initial_state(user_msg)

# Pass 1: Run graph until interrupt or completion
events = []
for evt in graph.stream(state, config=config):
    for node, upd in evt.items():
        events.append(node)
        print(f"  [NODE] {node}")
        if "pending_tool_call" in upd and upd["pending_tool_call"]:
            print(f"    -> pending_tool_call: {upd['pending_tool_call']}")

current_state = graph.get_state(config)
print("\n--- Graph State after Pass 1 ---")
print(f"Next nodes in queue: {current_state.next}")

PASS = 0
FAIL = 0

def check(label, condition, got=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {label}")
        PASS += 1
    else:
        print(f"  FAIL  {label}  | got: {got}")
        FAIL += 1

check("Graph interrupted for human approval", bool(current_state.next), current_state.next)

if current_state.next:
    print("\n>>> HITL APPROVAL INTERRUPT ACTIVE <<<")
    if current_state.tasks:
        for task in current_state.tasks:
            if task.interrupts:
                req = task.interrupts[0].value
                print(f"Approval Message: {req.get('message')}")
                actions = req.get("actions", [])
                print(f"Approval Actions: {actions}")
                if actions:
                    check("Action is book_train", actions[0].get("tool") == "book_train", actions[0].get("tool"))

    # Resume graph with user Approval APPROVED
    from langgraph.types import Command
    print("\n=== RESUMING WITH APPROVAL (approved=True) ===")
    resume_cmd = Command(resume={"approved": True, "reason": "User approved train booking"})

    for evt in graph.stream(resume_cmd, config=config):
        for node, upd in evt.items():
            print(f"  [RESUME NODE] {node}")

final_state = graph.get_state(config).values
print("\n=== FINAL STATE SUMMARY ===")
print(f"Intent: {final_state.get('intent_classification')}")
print(f"Extracted Entities: {final_state.get('extracted_entities')}")
bookings = final_state.get("booking_results", [])
print(f"Booking Results: {bookings}")
resp = final_state.get("final_response", "")
print(f"\nFinal Response ({len(resp)} chars):\n{resp[:500]}...\n")

check("Train booking confirmed", len(bookings) > 0 and bookings[0].get("type") == "train", bookings)
check("Booking ID format TRN-", bool(bookings and bookings[0].get("booking_id", "").startswith("TRN-")), bookings)
check("Final response set", bool(resp), "empty")

print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL TRAIN BOOKING TESTS PASSED SUCCESSFULLY!")
else:
    print("SOME TESTS FAILED - see log above")
