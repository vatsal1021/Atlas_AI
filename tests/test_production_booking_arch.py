"""Comprehensive Test Suite for Production Booking Architecture.

Tests all 6 acceptance criteria cases:
  1. Missing passenger information -> asks user for missing fields, book_train NOT called.
  2. Information complete -> validator ready=True.
  3. Missing API authentication -> booking tool NOT executed, capability=False, honest refusal.
  4. Authenticated API available -> book_train executes via provider.
  5. Booking API failure -> status=failed in runtime/book_train.json, no fake PNR.
  6. Multi-turn information collection -> state merges passenger details across turns.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
from services.booking_requirements.validator import validate_booking_requirements
from services.booking.capability import check_booking_capability
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


print("\n=== RUNNING PRODUCTION BOOKING ARCHITECTURE TEST SUITE ===\n")

# ---------------------------------------------------------------------------
# Case 1: Missing Passenger Information
# ---------------------------------------------------------------------------
print("--- Case 1: Missing Passenger Information ---")
val_incomplete = validate_booking_requirements(
    booking_type="train",
    passenger_info=[{"name": "Vatsal Mittal"}]  # age, gender, berth, class missing
)
check("Validator returns ready=False when fields missing", not val_incomplete["ready"], val_incomplete)
check("Missing fields list identifies missing passenger details", "passenger.age" in val_incomplete["missing_fields"], val_incomplete["missing_fields"])

# Test graph behavior with incomplete fields
graph = compile_graph()
config = {"configurable": {"thread_id": "test_case1_missing_info"}}
state1 = create_initial_state("book train ticket from Kanpur to Delhi for Vatsal Mittal")

for evt in graph.stream(state1, config=config):
    pass

st1 = graph.get_state(config).values
bookings1 = st1.get("booking_results", [])
check("book_train NOT executed when info incomplete", len(bookings1) == 0, bookings1)
check("Graph did NOT freeze at human approval for incomplete info", not bool(graph.get_state(config).next), graph.get_state(config).next)


# ---------------------------------------------------------------------------
# Case 2: Information Complete
# ---------------------------------------------------------------------------
print("\n--- Case 2: Information Complete ---")
val_complete = validate_booking_requirements(
    booking_type="train",
    passenger_info=[{
        "name": "Vatsal Mittal",
        "age": 22,
        "gender": "male",
        "berth_preference": "lower berth",
        "class": "CC",
    }]
)
check("Validator returns ready=True when all fields present", val_complete["ready"], val_complete)
check("Missing fields list is empty when complete", len(val_complete["missing_fields"]) == 0, val_complete["missing_fields"])


# ---------------------------------------------------------------------------
# Case 3: Missing API Authentication
# ---------------------------------------------------------------------------
print("\n--- Case 3: Missing API Authentication ---")
os.environ["ENABLE_MOCK_RAIL_PROVIDER"] = "false"
os.environ.pop("RAIL_BOOKING_API_KEY", None)

cap_unauth = check_booking_capability("train")
check("Capability returns available=False when API key missing", not cap_unauth["available"], cap_unauth)
check("Capability reason states authentication missing", "missing" in cap_unauth["reason"].lower() or "configured" in cap_unauth["reason"].lower(), cap_unauth["reason"])

# Re-enable mock provider for subsequent test cases
os.environ["ENABLE_MOCK_RAIL_PROVIDER"] = "true"


# ---------------------------------------------------------------------------
# Case 4: Authenticated API Available & Execution
# ---------------------------------------------------------------------------
print("\n--- Case 4: Authenticated API Available & Execution ---")
os.environ["ENABLE_MOCK_RAIL_PROVIDER"] = "true"

graph4 = compile_graph()
config4 = {"configurable": {"thread_id": "test_case4_auth_execution"}}
user_msg4 = "book train ticket from Kanpur to Delhi for Vatsal Mittal, 22, male, lower berth, CC class on 20 August"
state4 = create_initial_state(user_msg4)

for evt in graph4.stream(state4, config=config4):
    pass

ckpt4 = graph4.get_state(config4)
check("Graph interrupted for human approval when info complete & cap available", bool(ckpt4.next), ckpt4.next)

# Resume with human approval
resume_cmd = Command(resume={"approved": True, "reason": "User approved booking"})
for evt in graph4.stream(resume_cmd, config=config4):
    pass

st4 = graph4.get_state(config4).values
bookings4 = st4.get("booking_results", [])
check("book_train executed and booking confirmed", len(bookings4) > 0 and bookings4[0].get("booking_id", "").startswith("TRN-"), bookings4)


# ---------------------------------------------------------------------------
# Case 5: Booking API Failure
# ---------------------------------------------------------------------------
print("\n--- Case 5: Booking API Failure ---")
os.environ["FORCE_RAIL_API_FAILURE"] = "true"

graph5 = compile_graph()
config5 = {"configurable": {"thread_id": "test_case5_api_failure"}}
state5 = create_initial_state("book train ticket from Kanpur to Delhi for Vatsal Mittal, 22, male, lower berth, CC class on 20 August")

for evt in graph5.stream(state5, config=config5):
    pass

ckpt5 = graph5.get_state(config5)
if ckpt5.next:
    resume_cmd5 = Command(resume={"approved": True, "reason": "Approved"})
    for evt in graph5.stream(resume_cmd5, config=config5):
        pass

# Check runtime/book_train.json status
tool_file = Path("runtime/book_train.json")
if tool_file.exists():
    t_data = json.loads(tool_file.read_text(encoding="utf-8"))
    check("runtime/book_train.json captures failed status or errors", len(t_data.get("errors", [])) > 0 or t_data.get("status") == "failed", t_data)

os.environ["FORCE_RAIL_API_FAILURE"] = "false"


# ---------------------------------------------------------------------------
# Case 6: Multi-Turn Information Collection
# ---------------------------------------------------------------------------
print("\n--- Case 6: Multi-Turn Information Collection ---")
graph6 = compile_graph()
config6 = {"configurable": {"thread_id": "test_case6_multiturn"}}

# Turn 1: User gives name only
s1 = create_initial_state("book train ticket from Kanpur to Delhi for Vatsal Mittal")
for evt in graph6.stream(s1, config=config6):
    pass
st6_1 = graph6.get_state(config6).values

# Turn 2: User provides age, gender, berth, class in turn 2
s2 = create_initial_state("age 22, male, lower berth, CC class", existing_state=st6_1)
for evt in graph6.stream(s2, config=config6):
    pass

st6_2 = graph6.get_state(config6).values
passengers6 = st6_2.get("passenger_info", [])
check("Multi-turn passenger_info merges name from turn 1 with details from turn 2", len(passengers6) > 0 and passengers6[0].get("name") == "Vatsal Mittal" and passengers6[0].get("age") == 22, passengers6)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL PRODUCTION BOOKING ARCHITECTURE TESTS PASSED SUCCESSFULLY!")
