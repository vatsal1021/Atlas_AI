"""Test natural language approval resume fix for interrupted graph state."""

import sys
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
from ui.streamlit_app import _check_approval_intent
from langgraph.types import Command

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

# 1. Test helper intent classification
is_yes, is_no = _check_approval_intent("yeah go ahead")
check("Detect 'yeah go ahead' as approval", is_yes and not is_no, f"yes={is_yes}, no={is_no}")

is_yes2, is_no2 = _check_approval_intent("yes please move ahead and do the final booking")
check("Detect 'yes please move ahead' as approval", is_yes2 and not is_no2, f"yes={is_yes2}, no={is_no2}")

is_yes3, is_no3 = _check_approval_intent("no don't book it")
check("Detect 'no don't book it' as rejection", is_no3, f"yes={is_yes3}, no={is_no3}")

# 2. Test graph interrupt and resume with natural language intent command
graph = compile_graph()
thread_id = "test_approval_natural_resume"
config = {"configurable": {"thread_id": thread_id}}

user_prompt = "book the train ticket from kanpur to delhi on 20 august"
state_input = create_initial_state(user_prompt)

# Stream pass 1 until interrupt
for evt in graph.stream(state_input, config=config):
    pass

checkpoint = graph.get_state(config)
check("Graph interrupted at human_approval", bool(checkpoint.next), checkpoint.next)

# Simulate natural language user message "yeah go ahead" while interrupted
user_text = "yeah go ahead"
is_approved, is_rejected = _check_approval_intent(user_text)

if checkpoint.next and is_approved:
    resume_cmd = Command(resume={"approved": True, "reason": user_text})
    print("\n=== RESUMING INTERRUPT WITH Command(approved=True) ===")
    for evt in graph.stream(resume_cmd, config=config):
        for node, upd in evt.items():
            print(f"  [RESUME NODE] {node}")

final_checkpoint = graph.get_state(config)
final_state = final_checkpoint.values
bookings = final_state.get("booking_results", [])
resp = final_state.get("final_response", "")

check("Graph execution completed after resume", not bool(final_checkpoint.next), final_checkpoint.next)
check("Train booking confirmed after natural resume", len(bookings) > 0 and bookings[0].get("booking_id", "").startswith("TRN-"), bookings)
check("Final response generated", bool(resp), "empty")

print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("APPROVAL LOOP FIX TEST PASSED SUCCESSFULLY!")
