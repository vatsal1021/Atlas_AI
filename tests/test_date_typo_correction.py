"""Test Date Correction and Component Merging across Turns.

Verifies that:
  Turn 1: User provides "20th auagust 20206" (typo year).
  Turn 2: User corrects to "august 2026".
  Expected: Entity extraction retains day 20 and merges to "2026-08-20".
            Agent does NOT output "August 2026 is too far ahead" advisory.
"""

import sys

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


print("\n=== RUNNING DATE TYPO CORRECTION & MERGE TEST ===\n")

graph = compile_graph()
config = {"configurable": {"thread_id": "test_date_typo_merge"}}

# Turn 1: User provides date with typo year
print("--- Turn 1: Date with typo year ('20th auagust 20206') ---")
s1 = create_initial_state("book ticket from Lucknow to Kanpur 20th auagust 20206")
for evt in graph.stream(s1, config=config):
    pass

st1 = graph.get_state(config).values
r1 = st1.get("final_response", "")
e1 = st1.get("extracted_entities", {})
print("Turn 1 Extracted Entities:", e1)

# Turn 2: User provides spelling & year correction ("august 2026")
print("\n--- Turn 2: Date correction ('august 2026') ---")
s2 = create_initial_state("august 2026", existing_state=st1)
for evt in graph.stream(s2, config=config):
    pass

st2 = graph.get_state(config).values
r2 = st2.get("final_response", "")
e2 = st2.get("extracted_entities", {})
print("Turn 2 Extracted Entities:", e2)
print("\nTurn 2 Agent Response:\n", r2, "\n")

check(
    "start_date retains day 20 and merges year 2026 to '2026-08-20'",
    e2.get("start_date") in ("2026-08-20", "20 August 2026", "20th August 2026"),
    e2.get("start_date")
)

check(
    "Agent DOES NOT output far-future booking unavailable advisory for August 2026",
    "looking quite far ahead" not in r2.lower() and "not yet available in the booking systems" not in r2.lower(),
    r2
)

print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("DATE TYPO CORRECTION TEST PASSED SUCCESSFULLY!")
