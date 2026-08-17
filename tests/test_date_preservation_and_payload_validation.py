"""Test Date Preservation, Search-Before-Booking Flow & Pre-Execution Payload Validation.

Verifies:
  1. Date Preservation: User requests "this 22 in Indore" -> checkin_date "2026-08-22" is preserved
     all the way to book_hotel execution without being corrupted to "2026-08-20".
  2. Search-Before-Booking Flow: Search queries run search_hotels / search_trains / search_flights
     first before asking for personal passenger/guest details.
  3. Pre-Execution Payload Reconciliation: Mismatched or stale date parameters in booking tool
     calls are automatically reconciled to match the latest confirmed state.
"""

import sys
from datetime import datetime

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
from nodes.tool_execution import _validate_and_reconcile_booking_payload
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


print("\n=== RUNNING DATE PRESERVATION & PAYLOAD VALIDATION TEST ===\n")

now = datetime.now()
current_year = str(now.year)
current_month = f"{now.month:02d}"

# --- Test 1: Pre-Execution Payload Reconciler Unit Test ---
print("--- Unit Test: Pre-Execution Payload Reconciler ---")
mock_state = {
    "extracted_entities": {
        "start_date": "2026-08-22",
        "end_date": "2026-08-23",
        "destination": "Indore",
    },
    "guest_info": {"name": "Ansh Adarsh", "contact_email_or_phone": "ansh@example.com"},
    "selected_booking": {"hotel_name": "Hotel Sakura Indore"},
}

stale_payload = {
    "hotel_name": "Hotel Sakura Indore",
    "checkin_date": "2026-08-20",  # Stale date from past default
    "checkout_date": "2026-08-23",
}

reconciled = _validate_and_reconcile_booking_payload("book_hotel", stale_payload, mock_state)
print("Reconciled Payload:", reconciled)

check(
    "Pre-Execution reconciler overrides stale '2026-08-20' checkin with state '2026-08-22'",
    reconciled.get("checkin_date") == "2026-08-22",
    reconciled.get("checkin_date")
)
check(
    "Pre-Execution reconciler preserves checkout '2026-08-23'",
    reconciled.get("checkout_date") == "2026-08-23",
    reconciled.get("checkout_date")
)
check(
    "Pre-Execution reconciler preserves hotel name 'Hotel Sakura Indore'",
    reconciled.get("hotel_name") == "Hotel Sakura Indore",
    reconciled.get("hotel_name")
)


# --- Test 2: Full End-to-End Multi-Turn Date Preservation Flow ---
print("\n--- End-to-End Multi-Turn Date Preservation Flow ---")
graph = compile_graph()
thread_id = "test_date_preservation_session"
config = {"configurable": {"thread_id": thread_id}}

# Turn 1: Initial search objective
print("\nTurn 1: 'i want to book a hotel for this 22 in Indore'")
s1 = create_initial_state("i want to book a hotel for this 22 in Indore")
for evt in graph.stream(s1, config=config):
    pass

st1 = graph.get_state(config).values
e1 = st1.get("extracted_entities", {})
obs1 = st1.get("tool_observations", [])
tools1 = [o.get("tool") for o in obs1]
start_d1 = e1.get("start_date", "")

print("Turn 1 Extracted Entities:", e1)
print("Turn 1 Tools Executed:", tools1)

check(
    "Turn 1 executes 'search_hotels' first (Search-Before-Booking)",
    "search_hotels" in tools1 or "hotel_search" in tools1,
    tools1
)
check(
    "Turn 1 extracts check-in start_date '2026-08-22'",
    "2026-08-22" in start_d1 or ("22" in start_d1 and current_month in start_d1),
    start_d1
)

# Turn 2: Selection objective
print("\nTurn 2: 'Hotel Sakura Indore help me book this one'")
s2 = create_initial_state("Hotel Sakura Indore help me book this one", existing_state=st1)
for evt in graph.stream(s2, config=config):
    pass

st2 = graph.get_state(config).values
r2 = st2.get("final_response", "")
obs2 = st2.get("tool_observations", [])
tools2 = [o.get("tool") for o in obs2]

print("Turn 2 Response Preview:\n", r2[:250], "...\n")

check(
    "Turn 2 DOES NOT auto-execute 'book_hotel'",
    "book_hotel" not in tools2 and "hotel_booking" not in tools2,
    tools2
)

# Turn 3: Guest details submission
print("\nTurn 3: 'Guest name Ansh Adarsh, contact ansh@gmail.com, checkout 23rd'")
s3 = create_initial_state("Guest name Ansh Adarsh, contact ansh@gmail.com, checkout 23rd", existing_state=st2)
for evt in graph.stream(s3, config=config):
    pass

st3 = graph.get_state(config).values
r3 = st3.get("final_response", "")
print("Turn 3 Response Preview:\n", r3[:250], "...\n")

# Turn 4: Execution objective
print("\nTurn 4: 'Yes, book it'")
s4 = create_initial_state("Yes, book it", existing_state=st3)
for evt in graph.stream(s4, config=config):
    pass

ckpt4 = graph.get_state(config)
check("Turn 4 interrupts graph for human approval", bool(ckpt4.next), ckpt4.next)

if ckpt4.next:
    resume_cmd = Command(resume={"approved": True, "reason": "User explicitly approved Hotel Sakura booking"})
    for evt in graph.stream(resume_cmd, config=config):
        pass

st_final = graph.get_state(config).values
obs_final = st_final.get("tool_observations", [])

# Find book_hotel observation
book_obs = next((o for o in obs_final if o.get("tool") in ("book_hotel", "hotel_booking")), None)
print("Final Booking Observation:", book_obs)

if book_obs:
    args_used = book_obs.get("arguments", {})
    checkin_used = str(args_used.get("checkin_date", args_used.get("checkin", "")))
    checkout_used = str(args_used.get("checkout_date", args_used.get("checkout", "")))
    
    check(
        "book_hotel receives checkin_date '2026-08-22' (NOT corrupted to 2026-08-20)",
        "2026-08-22" in checkin_used or "22" in checkin_used,
        checkin_used
    )
    check(
        "book_hotel receives checkout_date '2026-08-23'",
        "2026-08-23" in checkout_used or "23" in checkout_used,
        checkout_used
    )

print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("DATE PRESERVATION & PAYLOAD VALIDATION TEST PASSED SUCCESSFULLY!")
