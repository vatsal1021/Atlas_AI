"""Test Exact User Conversation Flow (Section 11 of User Request).

Validates the exact control flow:
  Turn 1: User asks to book ticket from Lucknow to Kanpur.
  Turn 2: User selects Shatabdi Express 12004 14:00.
          -> Agent MUST ask for missing passenger details (Name, Age, Gender, Berth).
          -> Agent MUST NOT say "I do not have provider authentication" at this stage!
          -> Agent MUST NOT output generic travel recommendations (food, punctuality).
  Turn 3: User provides "Vatsal Mittal, 22, Male, Lower Berth".
          -> Information complete.
          -> Capability checked.
          -> If authenticated API available -> Booking Summary -> HITL Approval -> book_train.
          -> If authentication missing -> Honest refusal ("I have collected all details...").
"""

import os
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


print("\n=== RUNNING EXACT USER CONVERSATION FLOW TEST ===\n")

graph = compile_graph()
thread_id = "test_exact_user_conversation_flow"
config = {"configurable": {"thread_id": thread_id}}

# --- Turn 1: Initial booking search request ---
print("--- Turn 1: Initial Booking Request ---")
s1 = create_initial_state("Book a ticket from Lucknow to Kanpur for 20th August 2026.")
for evt in graph.stream(s1, config=config):
    pass

st1 = graph.get_state(config).values
r1 = st1.get("final_response", "")
print("Turn 1 Response preview:\n", r1[:150], "...\n")

# --- Turn 2: User selects specific train ---
print("--- Turn 2: Train Selection ---")
# Temporarily clear API key to test authentication check order
os.environ["ENABLE_MOCK_RAIL_PROVIDER"] = "false"
os.environ.pop("RAIL_BOOKING_API_KEY", None)

s2 = create_initial_state("Shatabdi Express 12004 14:00", existing_state=st1)
for evt in graph.stream(s2, config=config):
    pass

st2 = graph.get_state(config).values
r2 = st2.get("final_response", "")
print("Turn 2 Response:\n", r2, "\n")

check(
    "Turn 2 asks for required passenger details (Full name, Age, Gender, Berth)",
    "Full name" in r2 or "Age" in r2 or "Gender" in r2 or "Berth" in r2 or "passenger" in r2.lower(),
    r2
)
check(
    "Turn 2 DOES NOT say 'I currently do not have provider authentication'",
    "provider authentication" not in r2.lower() and "unauthenticated" not in r2.lower(),
    r2
)
check(
    "Turn 2 DOES NOT output generic recommendations (punctuality, food)",
    "punctuality" not in r2.lower() and "recommendations" not in r2.lower(),
    r2
)


# --- Turn 3: User provides passenger details ---
print("--- Turn 3: Passenger Details Submission ---")
# Case A: Authentication missing -> Honest refusal
s3_unauth = create_initial_state("Vatsal Mittal, 22, Male, Lower Berth, CC Class", existing_state=st2)
for evt in graph.stream(s3_unauth, config=config):
    pass

st3_unauth = graph.get_state(config).values
r3_unauth = st3_unauth.get("final_response", "")
print("Turn 3 (Unauthenticated Provider) Response:\n", r3_unauth, "\n")

check(
    "Turn 3 honest response states info collected but provider unauthenticated",
    "collected" in r3_unauth.lower() and "authenticated" in r3_unauth.lower() or "cannot execute" in r3_unauth.lower(),
    r3_unauth
)


# Case B: Authenticated API available -> HITL approval & execution
print("\n--- Turn 3 (Authenticated Provider Case) ---")
os.environ["ENABLE_MOCK_RAIL_PROVIDER"] = "true"

config_auth = {"configurable": {"thread_id": "test_exact_conv_auth"}}
s1_a = create_initial_state("Book a ticket from Lucknow to Kanpur for 20th August 2026.")
for evt in graph.stream(s1_a, config=config_auth):
    pass

st1_a = graph.get_state(config_auth).values
s2_a = create_initial_state("Shatabdi Express 12004 14:00", existing_state=st1_a)
for evt in graph.stream(s2_a, config=config_auth):
    pass

st2_a = graph.get_state(config_auth).values
s3_a = create_initial_state("Vatsal Mittal, 22, Male, Lower Berth, CC Class", existing_state=st2_a)
for evt in graph.stream(s3_a, config=config_auth):
    pass

ckpt_auth = graph.get_state(config_auth)
check("Turn 3 with auth interrupts graph for human approval", bool(ckpt_auth.next), ckpt_auth.next)

if ckpt_auth.next:
    resume_cmd = Command(resume={"approved": True, "reason": "User approved Shatabdi booking"})
    for evt in graph.stream(resume_cmd, config=config_auth):
        pass

st_final = graph.get_state(config_auth).values
bookings = st_final.get("booking_results", [])
check("book_train executed and ticket confirmed", len(bookings) > 0 and bookings[0].get("booking_id", "").startswith("TRN-"), bookings)


print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("EXACT USER CONVERSATION FLOW TEST PASSED SUCCESSFULLY!")
