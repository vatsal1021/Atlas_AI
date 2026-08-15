"""Multi-turn conversation memory integration test."""

import sys
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph.graph import compile_graph
from graph.planner_loop import create_initial_state

graph = compile_graph()
thread_id = "test_memory_turn_session"
config = {"configurable": {"thread_id": thread_id}}

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

def run_turn(user_msg: str) -> dict:
    existing = graph.get_state(config)
    existing_values = existing.values if existing else None
    state_input = create_initial_state(user_msg, existing_state=existing_values)
    
    for evt in graph.stream(state_input, config=config):
        for node, upd in evt.items():
            pass
            
    final_state = graph.get_state(config).values
    return final_state

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== TURN 1: User introduces name ===")
s1 = run_turn("Hi, my name is Vatsal, nice to meet you!")
resp1 = s1.get("final_response", "")
print(f"  Response: {resp1}")
check("Turn 1 response mentions Vatsal", "vatsal" in resp1.lower(), resp1)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== TURN 2: User asks for their name (Conversational Memory Test) ===")
s2 = run_turn("What is my name?")
resp2 = s2.get("final_response", "")
print(f"  Response: {resp2}")
check("Turn 2 recalls name 'Vatsal'", "vatsal" in resp2.lower(), resp2)

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== TURN 3: User shares trip parameters ===")
s3 = run_turn("I want to plan a 3-day trip to Jaipur for 2 people with a 20000 INR budget")
resp3 = s3.get("final_response", "")
entities3 = s3.get("extracted_entities", {})
print(f"  Extracted Entities: {entities3}")
check("Destination Jaipur extracted", entities3.get("destination") == "Jaipur", entities3.get("destination"))
check("Budget 20000 extracted", str(entities3.get("budget")) in ("20000", "20000.0"), entities3.get("budget"))

# ─────────────────────────────────────────────────────────────────────────────
print("\n=== TURN 4: User asks to recall trip details from state ===")
s4 = run_turn("Where am I planning to go and what is my budget?")
resp4 = s4.get("final_response", "")
print(f"  Response: {resp4}")
check("Turn 4 recalls Jaipur", "jaipur" in resp4.lower(), resp4)
check("Turn 4 recalls budget", "20" in resp4.lower() or "20,000" in resp4.lower() or "20000" in resp4.lower(), resp4)

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL MULTI-TURN MEMORY TESTS PASSED SUCCESSFULLY!")
else:
    print("SOME TESTS FAILED - see log above")
