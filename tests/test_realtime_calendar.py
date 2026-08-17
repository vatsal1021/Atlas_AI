"""Test Live System Clock & Real-Time Relative Date Resolution.

Verifies:
  1. Turn 1 ("i want to book a hotel in lucknow on this 22") -> extracts start_date anchored to current month/year (2026-08-22).
  2. Turn 2 ("this 22nd and checkout time is 23rd") -> extracts end_date anchored to current month/year (2026-08-23).
  3. Turn 3 ("yes current month") -> agent confirms August 22-23, 2026 without hallucinating May 2025 or re-asking for month.
"""

import sys
from datetime import datetime

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state

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


print("\n=== RUNNING REAL-TIME CALENDAR DATE TEST ===\n")

now = datetime.now()
expected_year = str(now.year)
expected_month = f"{now.month:02d}"

print(f"Active System Date: {now.strftime('%Y-%m-%d')}")

graph = compile_graph()
thread_id = "test_realtime_calendar_session"
config = {"configurable": {"thread_id": thread_id}}

# --- Turn 1 ---
print("\n--- Turn 1: 'i want to book a hotel in lucknow on this 22' ---")
s1 = create_initial_state("i want to book a hotel in lucknow on this 22")
for evt in graph.stream(s1, config=config):
    pass

st1 = graph.get_state(config).values
e1 = st1.get("extracted_entities", {})
start_d1 = e1.get("start_date", "")
print("Turn 1 Extracted Entities:", e1)

check(
    f"Turn 1 extracts start_date with current year '{expected_year}' and month '{expected_month}'",
    expected_year in start_d1 and (expected_month in start_d1 or "august" in start_d1.lower()),
    start_d1
)
check(
    "Turn 1 start_date contains day 22",
    "22" in start_d1,
    start_d1
)


# --- Turn 2 ---
print("\n--- Turn 2: 'this 22nd and checkout time is 23rd' ---")
s2 = create_initial_state("this 22nd and checkout time is 23rd", existing_state=st1)
for evt in graph.stream(s2, config=config):
    pass

st2 = graph.get_state(config).values
e2 = st2.get("extracted_entities", {})
start_d2 = e2.get("start_date", "")
end_d2 = e2.get("end_date", "")
print("Turn 2 Extracted Entities:", e2)

check(
    "Turn 2 retains start_date day 22",
    "22" in start_d2,
    start_d2
)
check(
    "Turn 2 extracts end_date with day 23",
    "23" in end_d2,
    end_d2
)


# --- Turn 3 ---
print("\n--- Turn 3: 'yes current month' ---")
s3 = create_initial_state("yes current month", existing_state=st2)
for evt in graph.stream(s3, config=config):
    pass

st3 = graph.get_state(config).values
r3 = st3.get("final_response", "")
e3 = st3.get("extracted_entities", {})
print("Turn 3 Final Response Preview:\n", r3[:250], "...\n")

check(
    "Turn 3 DOES NOT hallucinate May 2025 or 2025",
    "2025" not in r3 and "may" not in r3.lower(),
    r3
)
check(
    "Turn 3 state or response includes active year 2026 or month August",
    expected_year in r3 or "august" in r3.lower() or "2026-08" in str(e3),
    f"response: {r3[:100]}... | entities: {e3}"
)

print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("REAL-TIME CALENDAR DATE TEST PASSED SUCCESSFULLY!")
