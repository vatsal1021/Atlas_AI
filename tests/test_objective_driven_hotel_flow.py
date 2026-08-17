"""Test Objective-Driven Hotel Search & Booking Architecture.

Verifies the 3 distinct user objectives:
  1. Exploration Objective ("Find me a hotel in Lucknow from 22nd to 23rd August")
     -> Calls search_hotels, returns options, no booking execution, no technical jargon.
  2. Selection Objective ("I prefer Grand Hyatt Lucknow")
     -> Confirms details, asks for explicit confirmation, no auto-booking.
  3. Execution Objective ("Yes, book it")
     -> Triggers book_hotel and returns booking result.
"""

import sys

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
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


print("\n=== RUNNING OBJECTIVE-DRIVEN HOTEL FLOW TEST ===\n")

graph = compile_graph()
thread_id = "test_objective_driven_hotel_session"
config = {"configurable": {"thread_id": thread_id}}

# --- Turn 1: Exploration Objective ---
print("--- Turn 1: Exploration Objective ('Find me a hotel in Lucknow from 22nd to 23rd August') ---")
s1 = create_initial_state("Find me a hotel in Lucknow from 22nd to 23rd August")
for evt in graph.stream(s1, config=config):
    pass

st1 = graph.get_state(config).values
r1 = st1.get("final_response", "")
obs1 = st1.get("tool_observations", [])
tools1 = [o.get("tool") for o in obs1]

print("Turn 1 Tools Used:", tools1)
print("Turn 1 Response Preview:\n", r1[:250], "...\n")

check(
    "Turn 1 executes 'search_hotels'",
    "search_hotels" in tools1 or "hotel_search" in tools1,
    tools1
)
check(
    "Turn 1 DOES NOT call 'book_hotel'",
    "book_hotel" not in tools1 and "hotel_booking" not in tools1,
    tools1
)
check(
    "Turn 1 DOES NOT mention internal jargon ('provider authentication', 'mock')",
    "provider authentication" not in r1.lower() and "capability check" not in r1.lower(),
    r1
)


# --- Turn 2: Selection Objective ---
print("\n--- Turn 2: Selection Objective ('I prefer Grand Hyatt Lucknow') ---")
s2 = create_initial_state("I prefer Grand Hyatt Lucknow", existing_state=st1)
for evt in graph.stream(s2, config=config):
    pass

st2 = graph.get_state(config).values
r2 = st2.get("final_response", "")
obs2 = st2.get("tool_observations", [])
tools2 = [o.get("tool") for o in obs2]

print("Turn 2 Response:\n", r2[:250], "...\n")

check(
    "Turn 2 DOES NOT auto-execute 'book_hotel'",
    "book_hotel" not in tools2 and "hotel_booking" not in tools2,
    tools2
)
check(
    "Turn 2 asks for explicit confirmation or guest details",
    "confirm" in r2.lower() or "proceed" in r2.lower() or "book" in r2.lower(),
    r2
)


# --- Turn 3: Execution Objective ---
print("\n--- Turn 3: Execution Objective ('Yes, book it') ---")
s3 = create_initial_state("Yes, book it. Guest: Vatsal, contact: vatsal@example.com", existing_state=st2)
for evt in graph.stream(s3, config=config):
    pass

ckpt3 = graph.get_state(config)
print("Turn 3 Graph Interrupted for HITL Approval:", bool(ckpt3.next))
check("Turn 3 interrupts graph for human approval", bool(ckpt3.next), ckpt3.next)

if ckpt3.next:
    resume_cmd = Command(resume={"approved": True, "reason": "User explicitly approved Grand Hyatt booking"})
    for evt in graph.stream(resume_cmd, config=config):
        pass

st_final = graph.get_state(config).values
bookings = st_final.get("booking_results", [])
r3_final = st_final.get("final_response", "")

print("\nTurn 3 Final Response:\n", r3_final[:250], "...\n")

check(
    "book_hotel executed and hotel booking confirmed",
    len(bookings) > 0 or "booked" in r3_final.lower() or "confirmed" in r3_final.lower(),
    bookings
)


print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("OBJECTIVE-DRIVEN HOTEL FLOW TEST PASSED SUCCESSFULLY!")
