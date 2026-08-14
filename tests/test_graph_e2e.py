"""End-to-end test for the new AtlasAI graph architecture."""
import sys
import io

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state

graph = compile_graph()

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

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== TEST 1: Irrelevant input (greeting) ===")
state = create_initial_state("Hi! My name is Vatsal")
for evt in graph.stream(state, config={"configurable": {"thread_id": "t1"}}):
    for node, upd in evt.items():
        print(f"  [NODE] {node}")

final = graph.get_state({"configurable": {"thread_id": "t1"}}).values
check("intent=irrelevant", final.get("intent_classification") == "irrelevant", final.get("intent_classification"))
check("final_response set", bool(final.get("final_response")), "empty")
check("no planning_directive", not final.get("planning_directive"), final.get("planning_directive"))

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== TEST 2: Simple travel request (zero-tool path) ===")
state2 = create_initial_state("Give me a 2-day Jaipur itinerary for a couple with budget 15000 INR")
for evt in graph.stream(state2, config={"configurable": {"thread_id": "t2"}}):
    for node, upd in evt.items():
        print(f"  [NODE] {node}")

final2 = graph.get_state({"configurable": {"thread_id": "t2"}}).values
check("intent=relevant",    final2.get("intent_classification") == "relevant",         final2.get("intent_classification"))
check("entities extracted", bool(final2.get("extracted_entities")),                    "empty dict")
check("final_response set", bool(final2.get("final_response")),                        "empty")
check("no approval needed", not final2.get("approval_required"),                       final2.get("approval_required"))
resp2 = final2.get("final_response", "")
print(f"  Response ({len(resp2)} chars): {resp2[:300]}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== TEST 3: Missing info -> negotiation question ===")
state3 = create_initial_state("Book me a flight and hotel")
for evt in graph.stream(state3, config={"configurable": {"thread_id": "t3"}}):
    for node, upd in evt.items():
        print(f"  [NODE] {node}")

final3 = graph.get_state({"configurable": {"thread_id": "t3"}}).values
check("intent=relevant",    final3.get("intent_classification") == "relevant",         final3.get("intent_classification"))
check("negotiation triggered", final3.get("negotiation_status") == "needs_information", final3.get("negotiation_status"))
check("final_response is a question", bool(final3.get("final_response")),              "empty")
print(f"  Question: {final3.get('final_response', '')[:200]}")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED - see details above")
