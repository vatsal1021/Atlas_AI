# AtlasAI — New Architecture Implementation Specification

> **Status:** Design / Pre-implementation  
> **Author:** Antigravity (AI Coding Assistant)  
> **Date:** 2026-08-14  
> **Replaces:** The Phase 1-3 multi-loop graph defined in `graph/graph.py`

---

## Table of Contents
1. [Summary](#1-summary)
2. [Final Node List](#2-final-node-list)
3. [Responsibility of Every Node](#3-responsibility-of-every-node)
4. [LangGraph State Fields (`TripState`)](#4-langgraph-state-fields-tripstate)
5. [Conditional Edges and Routing Logic](#5-conditional-edges-and-routing-logic)
6. [ReAct / Tool-Calling Loop](#6-react--tool-calling-loop)
7. [Human Approval Flow](#7-human-approval-flow)
8. [Reflection and Replanning Behaviour](#8-reflection-and-replanning-behaviour)
9. [Single-Pass Execution Model](#9-single-pass-execution-model)
10. [Persistent State Across User Turns](#10-persistent-state-across-user-turns)
11. [Files to Create / Modify / Delete](#11-files-to-create--modify--delete)
12. [Mapping: Old Architecture → New Architecture](#12-mapping-old-architecture--new-architecture)
13. [Implementation Risks and Conflicts](#13-implementation-risks-and-conflicts)

---

## 1. Summary

The new architecture replaces the previous Phase 1-3 multi-loop graph (14 nodes, unbounded planning loops, sequential waterfalls) with a **single-pass, intent-driven, ReAct-centred graph** (9 active nodes + 2 extension stubs).

### Core Design Principles
- Every user message is **one graph invocation**, start to END.
- The only internal loop is the **ReAct ↔ ToolExecution** tool-calling cycle.
- Negotiation (clarification) happens via `END`-and-resume, not an in-graph loop.
- Critic is **optional** — gated by a lightweight `CriticGate` decision.
- `ExplainabilityNode` is **removed** — its responsibility moves into `RelevantResponseNode`.
- The agent answers **conversational messages** without running any planner machinery.

### New Graph (Mermaid)

```
START
  → IntentNode (Relevance Gate)
      ↓ irrelevant/empty
  → IrrelevantResponseNode → END
      ↓ relevant
  → EntityExtractNode
      → NegotiationClassificationNode
          ↓ needs_information
          → NegotiationQuestionNode → END
          ↓ information_complete
          → IntentNode (Path Gate)
              ↓ plan
              → PlanProposalDirectiveNode → ReactNode
              ↓ direct_execute
              → ReactNode
                  ↓ act
                  → ToolExecutionNode → ReactNode (loop)
                  ↓ critical action
                  → HumanApprovalNode
                      ↓ approved → ToolExecutionNode
                      ↓ rejected → ReactNode
                  ↓ respond / complete
                  → ReflectNode
                      ↓ needs_more_work → ReactNode
                      ↓ complete → CriticGate
                          ↓ skip → RelevantResponseNode → END
                          ↓ critic_required → CriticNode → RelevantResponseNode → END
```

---

## 2. Final Node List

| # | Node Name (constant) | File |
|---|---|---|
| 1 | `intent_node` | `nodes/intent_node.py` |
| 2 | `irrelevant_response` | `nodes/irrelevant_response.py` |
| 3 | `entity_extract` | `nodes/entity_extract.py` |
| 4 | `negotiation_classification` | `nodes/negotiation_classification.py` |
| 5 | `negotiation_question` | `nodes/negotiation_question.py` |
| 6 | `plan_proposal` | `nodes/plan_proposal.py` |
| 7 | `react` | `nodes/react.py` |
| 8 | `tool_execution` | `nodes/tool_execution.py` |
| 9 | `human_approval` | `nodes/human_approval.py` *(updated)* |
| 10 | `reflect` | `nodes/reflect.py` |
| 11 | `critic_gate` | `nodes/critic_gate.py` |
| 12 | `critic` | `nodes/critic.py` *(updated)* |
| 13 | `relevant_response` | `nodes/relevant_response.py` |

**Supporting capability stubs (no graph nodes):**
- `ToolSelectionMemory` — helper class used *inside* `react` node
- `MultiAgentCollaboration` — interface stub called from `plan_proposal`

**Old nodes being removed:** `goal_understanding`, `goal_decomposition`, `objective_planner`, `capability_dispatcher`, `evidence_aggregator`, `world_model`, `goal_evaluator`, `reflection`, `explainability`, `action_dispatcher`, `meta_reasoner`, `memory_update`

---

## 3. Responsibility of Every Node

### 3.1 `IntentNode` — Dual Role (Relevance Gate + Path Gate)
This node is called **twice** in the logical flow but is **one node function** that reads `intent_gate_mode` from state to know which role it is playing.

**Role A — Relevance Gate (entry point):**
- Receives raw `user_input`.
- Makes a fast (temperature=0, small prompt) LLM call to classify intent as:
  - `relevant` — a travel-related request or question
  - `irrelevant` — off-topic, greeting, chitchat, non-travel question
  - `empty` — blank or malformed input
- Writes `intent_classification` and `intent_gate_mode = "relevance"` to state.
- Does NOT run entity extraction or any planning logic.

**Role B — Path Gate (called after NegotiationClassificationNode says `information_complete`):**
- Reads the extracted entities and conversation history.
- Determines execution path:
  - `plan` — the request is complex, multi-step, or ambiguous enough to benefit from a structured plan directive
  - `direct_execute` — the request is clear and bounded; go straight to ReAct
- Writes `path_decision` to state.

**Routing output:** `relevant | irrelevant | empty` (Role A); `plan | direct_execute` (Role B)

---

### 3.2 `IrrelevantResponseNode`
- Triggered when `IntentNode` returns `irrelevant` or `empty`.
- Generates a short, natural, friendly response without any planning machinery.
- Examples: greeting back, explaining AtlasAI's purpose, politely declining off-topic requests.
- Writes `final_response` to state.
- Routes directly to `END`.

---

### 3.3 `EntityExtractNode` (`entity_extract`)
- Only triggered when intent is `relevant`.
- Performs LLM-based structured extraction of travel entities from `user_input` AND the existing `conversation_history` (persistent state from prior turns).
- Extracts:
  - `destination`, `origin`, `budget`, `currency`, `dates`, `duration`, `travelers`
  - `travel_preferences` (luxury, backpacker, family, adventure, etc.)
  - `constraints` (dietary, accessibility, visa, etc.)
  - `known_entities` (hotels/airlines already mentioned in conversation)
- Merges newly extracted entities with any previously persisted entities (partial information from prior turns) — this is how the agent builds up a complete profile across multiple negotiation rounds.
- Writes `extracted_entities` to state.

---

### 3.4 `NegotiationClassificationNode` (`negotiation_classification`)
- Reads `extracted_entities`, `conversation_history`, and `negotiation_history`.
- Determines whether the agent has **enough information** to proceed with planning or execution for the user's stated objective.
- "Enough information" is defined dynamically by the LLM — not a fixed checklist.
  - A simple request ("Give me a Jaipur weekend itinerary") may need zero additional info.
  - A booking request ("Book me a flight and hotel") needs destination, dates, budget, traveler count.
- Output:
  - `needs_information` — one or more critical pieces are missing
  - `information_complete` — sufficient to proceed
- When `needs_information`, also writes `missing_fields: list[str]` and `negotiation_reasoning: str` to state.
- Does NOT generate the question — that is `NegotiationQuestionNode`'s job.

---

### 3.5 `NegotiationQuestionNode` (`negotiation_question`)
- Only triggered when `NegotiationClassificationNode` says `needs_information`.
- Reads `missing_fields`, `negotiation_history`, `conversation_history`.
- Generates ONE contextual follow-up question (or at most a grouped question) that will elicit the most critical missing information.
- The question must be:
  - Conversational in tone, not a form-fill request
  - Context-aware (references what the user already said)
  - Non-repetitive (checks `negotiation_history` to avoid re-asking)
- Writes `final_response` (the question text) and appends to `negotiation_history`.
- Routes to `END` — the next user reply starts a new graph pass that will re-enter at `IntentNode`.

---

### 3.6 `PlanProposalDirectiveNode` (`plan_proposal`)
- Only triggered when `PathGate` returns `plan`.
- Produces a **structured planning directive** that `ReactNode` will use as its guiding objective. This is NOT tool execution — it is thinking and structuring.
- Directive contains:
  ```json
  {
    "objective": "string — the primary goal",
    "constraints": ["list of hard constraints"],
    "required_decisions": ["list of decisions the agent must make"],
    "success_criteria": ["list of verifiable outcomes"],
    "known_assumptions": ["list of inferred context"]
  }
  ```
- Also writes `multi_agent_hint` — a lightweight struct that identifies which specialised sub-agent roles would be relevant (Travel Planner, Budget Agent, Local Expert, Booking Specialist). This is the extension point for future multi-agent collaboration.
- Writes `planning_directive` to state.
- Always routes to `ReactNode`.

---

### 3.7 `ReactNode` (`react`)
- The **central reasoning engine** of the new architecture.
- Implements the ReAct (Reason + Act) pattern.
- On each invocation, it:
  1. Reads `planning_directive` (if set), `extracted_entities`, `tool_observations` (prior tool results), `tool_selection_memory`, `conversation_history`.
  2. Reasons over what has been done and what still needs to be done.
  3. Makes **one of three decisions**:
     - `act` — selects a tool and writes `pending_tool_call: {tool, arguments, reasoning}` to state
     - `critical_action` — selects a consequential tool (booking/payment/cancellation/reservation) and writes `pending_tool_call` + `requires_approval: true`
     - `respond` / `complete` — determines enough work has been done and writes `react_conclusion` to state
- Uses `ToolSelectionMemory` to prefer tools with high success rates and avoid recently failed tools.
- The tool ordering is **fully dynamic** — determined by the LLM in each reasoning step.
- Can choose to respond WITHOUT any tool call (e.g., generating an itinerary from knowledge alone).
- Has a **max_react_iterations** guard in state to prevent runaway loops.
- Writes: `pending_tool_call`, `requires_approval`, `react_reasoning_log`, `react_iteration`.

---

### 3.8 `ToolExecutionNode` (`tool_execution`)
- Reads `pending_tool_call` from state.
- Resolves the tool name against the **Tool Registry** (existing `TOOL_REGISTRY` in `app/settings.py`, extended).
- Validates arguments against the tool's expected schema.
- Executes the tool function.
- Writes the result into `tool_observations: list[{tool, arguments, result, status, timestamp}]`.
- On success: routes back to `ReactNode`.
- On failure: writes error into `tool_observations` (marked as failed) and routes back to `ReactNode` — ReAct decides how to recover, not a separate meta-reasoner.

---

### 3.9 `HumanApprovalNode` (`human_approval`)
- **Updated** from the existing implementation — same `interrupt()` mechanism is preserved.
- Triggered only when `ReactNode` sets `requires_approval: true`.
- Reads `pending_tool_call` and generates a dynamic, friendly approval message using the LLM (this already works in the current implementation).
- Uses `langgraph.types.interrupt()` to pause the graph.
- On resume:
  - `approved: true` → routes to `ToolExecutionNode` (executes the approved action)
  - `approved: false` → writes rejection + reason to state, routes back to `ReactNode` so it can reason about an alternative
- The existing `ApprovalRequest`, `ApprovalResponse`, `ApprovalAction`, `ApprovalStatus`, and `ActionType` schemas from `schemas/approval_schema.py` are **fully preserved**.

---

### 3.10 `ReflectNode` (`reflect`)
- Triggered when `ReactNode` says `respond` or `complete`.
- Evaluates whether the work done is actually sufficient, by checking:
  - Is the `objective` (from `planning_directive` or extracted entities) satisfied?
  - Are all hard `constraints` met?
  - Are tool results valid and non-contradictory?
  - Is there enough information to generate a high-quality response?
  - For zero-tool plans: is the response ready as-is?
- Output decision:
  - `needs_more_work` — routes back to `ReactNode` with `reflect_feedback` written to state (ReAct reads this)
  - `complete` — routes to `CriticGate`
- Has a **max_reflect_iterations** guard to prevent infinite reflect-react cycles.
- A plan with zero tool calls can pass reflection — e.g., a Jaipur itinerary generated from LLM knowledge.

---

### 3.11 `CriticGate` (`critic_gate`)
- A **lightweight decision function** (not a full LLM call — uses simple heuristics or a fast classification call).
- Determines whether the request/plan is complex or high-risk enough to warrant full Critic review.
- Triggers Critic for:
  - Multi-city, multi-leg itineraries
  - Budget-constrained plans where constraints may conflict
  - Plans involving booking/payment actions
  - Requests with high ambiguity or conflicting user preferences
  - Plans where ReAct had to retry or recover from tool failures
- Skips Critic for:
  - Simple informational requests (weather, visa info)
  - Single-destination short itineraries
  - Conversational responses
- Output: `skip | critic_required`

---

### 3.12 `CriticNode` (`critic`)
- **Updated** from existing implementation.
- Only runs when `CriticGate` says `critic_required`.
- Challenges the plan/response by checking for:
  - Internal contradictions (e.g., budget vs. chosen hotels)
  - Missing required information
  - Risk factors the agent should flag to the user
  - Logical errors in the itinerary
- Does NOT send the plan back for replanning (no `OBJECTIVE_PLANNER` loop). Instead, writes `critic_notes: list[str]` to state which `RelevantResponseNode` uses to enrich its response with warnings/trade-offs.
- Writes `critic_notes` and `critic_risk_level: low | medium | high`.

---

### 3.13 `RelevantResponseNode` (`relevant_response`)
- The **final response generator** for all travel-related requests.
- Replaces both `ExplainabilityNode` and the final output step from `ActionDispatcher`.
- Reads: `planning_directive`, `tool_observations`, `react_reasoning_log`, `extracted_entities`, `critic_notes` (if set), `reflect_feedback` (if set).
- Generates a single, comprehensive final response containing:
  - **Answer** — the plan, itinerary, booking summary, or answer to the question
  - **Reasoning / Justification** — why these choices were made
  - **Recommendations** — "you should also consider…"
  - **Risks and Trade-offs** — budget risks, cancellation policies, weather caveats
  - **Warnings** — from Critic if critic ran, or from tool results
- Writes `final_response` (str) and `response_metadata` (dict) to state.
- Routes to `END`.

---

## 4. LangGraph State Fields (`TripState`)

The `TripState` TypedDict in `graph/state.py` will be **fully replaced** with the following schema. Fields from the old schema that are still needed are mapped across.

```python
class TripState(TypedDict, total=False):

    # ── Input ──────────────────────────────────────────────────────────
    user_input: str                        # current user message
    conversation_history: list[dict]       # [{role, content}] across all turns
    thread_id: str                         # session identifier for persistence

    # ── Intent ─────────────────────────────────────────────────────────
    intent_classification: str             # relevant | irrelevant | empty
    intent_gate_mode: str                  # relevance | path
    path_decision: str                     # plan | direct_execute

    # ── Entity Extraction ───────────────────────────────────────────────
    extracted_entities: dict               # destination, budget, dates, etc.
    # Preserves: parsed_goal → merged into extracted_entities

    # ── Negotiation ─────────────────────────────────────────────────────
    negotiation_status: str                # needs_information | information_complete
    missing_fields: list[str]              # what is missing
    negotiation_reasoning: str             # why information is incomplete
    negotiation_history: list[dict]        # [{question, answer}] per turn

    # ── Planning Directive ──────────────────────────────────────────────
    planning_directive: dict               # objective, constraints, decisions, success_criteria
    multi_agent_hint: dict                 # future multi-agent extension point

    # ── ReAct Loop ──────────────────────────────────────────────────────
    react_decision: str                    # act | critical_action | respond | complete
    pending_tool_call: dict                # {tool, arguments, reasoning}
    requires_approval: bool                # triggers HumanApprovalNode
    tool_observations: list[dict]          # [{tool, args, result, status, timestamp}]
    react_reasoning_log: list[str]         # chain-of-thought entries
    react_iteration: int                   # current ReAct step
    max_react_iterations: int              # guard against runaway loops (default: 8)
    # Preserves: tool_results → replaced by tool_observations
    # Preserves: tool_stats → moved into tool_selection_memory

    # ── Tool Selection Memory ───────────────────────────────────────────
    tool_selection_memory: dict            # {tool_name: {success_rate, avg_latency, failures}}

    # ── Human Approval ──────────────────────────────────────────────────
    approval_required: bool
    approval_status: str                   # pending | approved | rejected | not_needed
    approval_reason: str                   # rejection reason
    # Preserves: approval_required, approval_status, approval_reason — UNCHANGED

    # ── Reflection ──────────────────────────────────────────────────────
    reflect_decision: str                  # needs_more_work | complete
    reflect_feedback: str                  # guidance written back to ReAct
    reflect_iteration: int
    max_reflect_iterations: int            # default: 3

    # ── Critic ──────────────────────────────────────────────────────────
    critic_gate_decision: str              # skip | critic_required
    critic_notes: list[str]               # issues found
    critic_risk_level: str                 # low | medium | high
    # Preserves: critic_feedback → renamed to critic_notes

    # ── Response ────────────────────────────────────────────────────────
    final_response: str                    # the text shown to the user
    response_metadata: dict                # reasoning, recommendations, risks

    # ── Memory / Persistence ────────────────────────────────────────────
    memory_context: dict                   # user preferences (existing, preserved)
    session_summary: dict                  # summary of this session (preserved)

    # ── Booking Results ─────────────────────────────────────────────────
    booking_results: list[dict]            # preserved from old schema
    payment_results: list[dict]            # preserved from old schema

    # ── Error / Meta ────────────────────────────────────────────────────
    errors: list[dict]                     # error log (preserved)
    iteration_count: int                   # total graph iterations (preserved)
```

**Fields removed from old schema** (replaced by new equivalents):
- `parsed_goal` → `extracted_entities`
- `sub_goals` → `planning_directive.required_decisions`
- `current_plan`, `pending_tool_calls` → `pending_tool_call` (singular, per ReAct step)
- `planner_iteration`, `planning_complete` → `react_iteration`, `react_decision`
- `planner_reasoning` → `react_reasoning_log`
- `evidence`, `world_facts` → `tool_observations`
- `goal_status`, `goal_satisfied`, `evaluation_reasoning` → `reflect_decision`, `reflect_feedback`
- `reflection_gaps`, `reflection_notes` → `reflect_feedback`
- `critic_should_revise`, `critic_feedback` → `critic_notes`, `critic_risk_level`
- `explanation` → `response_metadata`
- `failure_history`, `recovery_attempts`, `max_recovery_attempts` → removed (ReAct handles recovery internally via `tool_observations`)
- `max_iterations`, `max_revisions` → `max_react_iterations`, `max_reflect_iterations`
- `revision_count` → removed

---

## 5. Conditional Edges and Routing Logic

All routing functions live in `graph/router.py` (rewritten). Each function takes `TripState` and returns a string node name.

```
graph/edges.py  ← all node name constants redefined here

INTENT_NODE            = "intent_node"
IRRELEVANT_RESPONSE    = "irrelevant_response"
ENTITY_EXTRACT         = "entity_extract"
NEGOTIATION_CLASSIFY   = "negotiation_classification"
NEGOTIATION_QUESTION   = "negotiation_question"
PLAN_PROPOSAL          = "plan_proposal"
REACT                  = "react"
TOOL_EXECUTION         = "tool_execution"
HUMAN_APPROVAL         = "human_approval"
REFLECT                = "reflect"
CRITIC_GATE            = "critic_gate"
CRITIC                 = "critic"
RELEVANT_RESPONSE      = "relevant_response"
```

### Routing Table

| From | Condition | To |
|---|---|---|
| `IntentNode` (Relevance Gate) | `irrelevant` or `empty` | `IrrelevantResponseNode` |
| `IntentNode` (Relevance Gate) | `relevant` | `EntityExtractNode` |
| `EntityExtractNode` | always | `NegotiationClassificationNode` |
| `NegotiationClassificationNode` | `needs_information` | `NegotiationQuestionNode` |
| `NegotiationClassificationNode` | `information_complete` | `IntentNode` (Path Gate) |
| `IntentNode` (Path Gate) | `plan` | `PlanProposalDirectiveNode` |
| `IntentNode` (Path Gate) | `direct_execute` | `ReactNode` |
| `PlanProposalDirectiveNode` | always | `ReactNode` |
| `ReactNode` | `act` | `ToolExecutionNode` |
| `ReactNode` | `critical_action` | `HumanApprovalNode` |
| `ReactNode` | `respond` or `complete` | `ReflectNode` |
| `ReactNode` | `max_react_iterations exceeded` | `ReflectNode` (forced) |
| `ToolExecutionNode` | always (success or failure) | `ReactNode` |
| `HumanApprovalNode` | `approved` | `ToolExecutionNode` |
| `HumanApprovalNode` | `rejected` | `ReactNode` |
| `ReflectNode` | `needs_more_work` AND `reflect_iteration < max` | `ReactNode` |
| `ReflectNode` | `complete` OR `max_reflect_iterations exceeded` | `CriticGate` |
| `CriticGate` | `skip` | `RelevantResponseNode` |
| `CriticGate` | `critic_required` | `CriticNode` |
| `CriticNode` | always | `RelevantResponseNode` |
| `RelevantResponseNode` | always | `END` |
| `IrrelevantResponseNode` | always | `END` |
| `NegotiationQuestionNode` | always | `END` |

---

## 6. ReAct / Tool-Calling Loop

The only **internal loop** in the graph is between `ReactNode` and `ToolExecutionNode`.

### Loop Mechanics
1. `ReactNode` selects a tool → writes `pending_tool_call = {tool, args, reasoning}`.
2. `ToolExecutionNode` executes → appends `{tool, args, result, status}` to `tool_observations`.
3. Control returns to `ReactNode`.
4. ReAct reads the new `tool_observations` entry and decides next action.
5. This continues until ReAct decides `respond` or `complete`.

### Loop Guard
- `react_iteration` increments on every ReAct invocation.
- When `react_iteration >= max_react_iterations` (default: 8), the router forces `ReflectNode` regardless of `react_decision`.
- This prevents runaway loops.

### Tool Selection Memory
- `ToolSelectionMemory` is a **helper class** (not a graph node) used inside `ReactNode`.
- Located at `graph/tool_selection_memory.py`.
- Stores per-session: tool success rates, avg latency, failure reasons.
- ReAct prompt includes a summary: "Tools you've tried this session: …"
- Updated after every `ToolExecutionNode` call.

### Zero-Tool Paths
A request can complete the ReAct loop with **zero tool calls**:
- ReAct reads the `planning_directive` and determines it can answer from LLM knowledge.
- Sets `react_decision = "respond"` without ever choosing `act`.
- `ReflectNode` sees `tool_observations = []` and evaluates if the response is still complete.
- If yes → proceeds to `CriticGate → RelevantResponseNode`.

---

## 7. Human Approval Flow

### Trigger Condition
`HumanApprovalNode` is triggered ONLY when `ReactNode` sets `requires_approval: true`.

`requires_approval` is set when the tool selected belongs to the irreversible set:
```python
IRREVERSIBLE_TOOLS = {
    "book_flight", "book_hotel",
    "make_reservation", "process_payment",
    "cancel_booking",  # new
}
```

### Approval Message Generation
- Same as the existing implementation: LLM composes a friendly message from `pending_tool_call`.
- Example: *"I've found an IndiGo flight from Delhi to Jaipur on Oct 15 for ₹4,200. Shall I book it?"*
- Uses existing `ApprovalRequest` / `ApprovalResponse` / `ApprovalAction` schemas — **no changes needed**.

### `interrupt()` Mechanism
- The existing `langgraph.types.interrupt(approval_request.model_dump())` call is preserved exactly.
- `MemorySaver` checkpointing (in `graph/graph.py`) handles pause and resume.
- The Streamlit UI resumes the graph with `Command(resume={approved: true/false, reason: ...})` — this is already implemented in `ui/components/approval_card.py`.

### On Rejection
- `approval_reason` is written to state.
- Router sends back to `ReactNode`.
- ReAct reads the rejection from `tool_observations` (the failed/rejected action is logged there) and reasons about an alternative — e.g., finding a different flight, adjusting the budget.

---

## 8. Reflection and Replanning Behaviour

### What `ReflectNode` checks
1. **Objective satisfied?** — Does the result of tool calls meet the `planning_directive.objective`?
2. **Constraints satisfied?** — Are all hard constraints (budget, dates, preferences) honoured?
3. **Tool results valid?** — Are tool results non-empty, non-contradictory, and relevant?
4. **Response ready?** — Is there sufficient information for `RelevantResponseNode` to generate a high-quality response?
5. **Zero-tool case** — If no tools were called, can the agent still generate a valuable response?

### Replanning vs. simple retry
- If `ReflectNode` says `needs_more_work`, it writes a `reflect_feedback` string to state.
- `ReactNode` reads `reflect_feedback` on its next iteration and uses it to adjust its reasoning.
- If the planning directive itself is infeasible (e.g., budget too low for the selected hotels), `reflect_feedback` will say so explicitly, and ReAct will generate a different tool call or revise its response.

### Loop guard
- `reflect_iteration` is incremented each time `ReflectNode` says `needs_more_work`.
- When `reflect_iteration >= max_reflect_iterations` (default: 3), routing forces `complete` → `CriticGate`.

---

## 9. Single-Pass Execution Model

Each user message results in **exactly one graph invocation** (one call to `graph.stream()` or `graph.invoke()`).

### What "single-pass" means
```
User message → graph.invoke(state) → final_response → END
```

No node should create an unconditional back-edge to `IntentNode` or `EntityExtractNode`.

### The only exception: negotiation
When `NegotiationClassificationNode` → `NegotiationQuestionNode` → `END`, the graph has completed its pass. The follow-up user reply starts a **new graph invocation**. Persisted state (via `MemorySaver` + `thread_id`) carries `extracted_entities`, `negotiation_history`, and `conversation_history` across this boundary.

### Preventing uncontrolled loops
- `max_react_iterations` guard (ReAct ↔ Tool loop)
- `max_reflect_iterations` guard (Reflect → ReAct loop)
- No unconditional back-edges to the beginning of the graph
- `IntentNode` is the entry point and is never re-entered within a single pass

---

## 10. Persistent State Across User Turns

### Mechanism
LangGraph `MemorySaver` with `thread_id` is already implemented. **No changes needed to the checkpointing infrastructure.**

The `config = {"configurable": {"thread_id": session_id}}` is already set in both `app/main.py` and `ui/streamlit_app.py`.

### What persists
| Field | Purpose |
|---|---|
| `conversation_history` | Full turn-by-turn chat history |
| `extracted_entities` | Accumulated entity knowledge across negotiation rounds |
| `negotiation_history` | Questions asked and answers given |
| `tool_selection_memory` | Per-session tool performance stats |
| `booking_results` / `payment_results` | Confirmed bookings from this session |
| `memory_context` | User preferences loaded from long-term memory |

### How new turns interact with persisted state
At the start of every new graph invocation:
1. `EntityExtractNode` reads both `user_input` (new message) AND `extracted_entities` (prior state), and merges.
2. `NegotiationClassificationNode` reads the combined picture to determine if information is now complete.
3. `ReactNode` reads `tool_observations` from the prior turn (if present) as context.
4. `conversation_history` is appended by `RelevantResponseNode` and `IrrelevantResponseNode` at END.

### Long-term memory (future)
`memory_context` (loaded from ChromaDB / disk via `tools/memory.py`) is preserved as-is. The `EntityExtractNode` can optionally load user preferences at startup.

---

## 11. Files to Create / Modify / Delete

### NEW files

| File | Purpose |
|---|---|
| `nodes/intent_node.py` | IntentNode (dual-role: relevance gate + path gate) |
| `nodes/irrelevant_response.py` | IrrelevantResponseNode |
| `nodes/entity_extract.py` | EntityExtractNode |
| `nodes/negotiation_classification.py` | NegotiationClassificationNode |
| `nodes/negotiation_question.py` | NegotiationQuestionNode |
| `nodes/plan_proposal.py` | PlanProposalDirectiveNode |
| `nodes/react.py` | ReactNode (ReAct engine) |
| `nodes/tool_execution.py` | ToolExecutionNode |
| `nodes/reflect.py` | ReflectNode |
| `nodes/critic_gate.py` | CriticGate (lightweight classifier) |
| `nodes/relevant_response.py` | RelevantResponseNode |
| `graph/tool_selection_memory.py` | ToolSelectionMemory helper class |
| `prompts/intent.yaml` | Prompt for IntentNode (relevance classification) |
| `prompts/entity_extract.yaml` | Prompt for EntityExtractNode |
| `prompts/negotiation_classification.yaml` | Prompt for NegotiationClassificationNode |
| `prompts/negotiation_question.yaml` | Prompt for NegotiationQuestionNode |
| `prompts/plan_proposal.yaml` | Prompt for PlanProposalDirectiveNode |
| `prompts/react.yaml` | ReAct reasoning prompt |
| `prompts/reflect.yaml` | Reflection evaluation prompt |
| `prompts/relevant_response.yaml` | Final response generation prompt |
| `docs/architecture_implementation.md` | This file |

### MODIFY (existing files, targeted changes)

| File | Changes |
|---|---|
| `graph/graph.py` | Full rewrite — remove old nodes, add new nodes, rewire all edges |
| `graph/state.py` | Full rewrite — new `TripState` schema (see §4) |
| `graph/edges.py` | Full rewrite — new node name constants |
| `graph/router.py` | Full rewrite — new routing functions |
| `graph/planner_loop.py` | Update `create_initial_state()` to match new state schema |
| `nodes/human_approval.py` | Targeted update — adapt to read `pending_tool_call` instead of `pending_tool_calls` |
| `nodes/critic.py` | Targeted update — remove `planning_complete` write, write `critic_notes` instead |
| `app/settings.py` | Add new feature flags; update `TOOL_REGISTRY` |
| `ui/streamlit_app.py` | Update response rendering to read `final_response` from state |

### DELETE (dead code from old architecture)

| File | Reason |
|---|---|
| `nodes/goal_understanding.py` | Replaced by `entity_extract.py` |
| `nodes/goal_decomposition.py` | Replaced by `plan_proposal.py` |
| `nodes/objective_planner.py` | Replaced by `react.py` |
| `nodes/capability_dispatcher.py` | Replaced by `tool_execution.py` |
| `nodes/evidence_aggregator.py` | Replaced by `tool_observations` in state |
| `nodes/world_model.py` | Replaced by `tool_observations` in state |
| `nodes/goal_evaluator.py` | Replaced by `reflect.py` |
| `nodes/reflection.py` | Replaced by `reflect.py` |
| `nodes/explainability.py` | Functionality merged into `relevant_response.py` |
| `nodes/action_dispatcher.py` | Replaced by `tool_execution.py` |
| `nodes/meta_reasoner.py` | Recovery handled inside `react.py` via `tool_observations` |
| `nodes/memory_update.py` | Memory update happens at `RelevantResponseNode` before `END` |
| `prompts/evaluator.yaml` | Old goal evaluator prompt |
| `prompts/goal_decomposition.yaml` | Old goal decomposition prompt |
| `prompts/goal_understanding.yaml` | Old goal understanding prompt |
| `prompts/planner.yaml` | Old planner prompt |
| `prompts/world_model.yaml` | Old world model prompt |
| `prompts/explainability.yaml` | Old explainability prompt |
| `prompts/meta_reasoner.yaml` | Old meta-reasoner prompt |

### PRESERVE UNCHANGED

| File | Reason |
|---|---|
| `app/tracing.py` | Full observability system — no changes needed |
| `app/config.py` | Settings loader — no changes |
| `services/llm.py` | LLM factory — no changes |
| `services/prompt_loader.py` | YAML prompt loader — no changes |
| `schemas/approval_schema.py` | All approval schemas preserved exactly |
| `schemas/tool_schema.py` | Tool result schemas preserved |
| `tools/` directory (all files) | All tool implementations preserved |
| `agents/` directory (all files) | Multi-agent stubs preserved as extension points |
| `memory/` directory | Long-term memory preserved |
| `runtime/` directory | Trace output directory preserved |
| `ui/components/approval_card.py` | Human approval UI — no changes needed |
| `ui/components/sidebar.py` | May need minor update for new state fields |
| `ui/components/chat.py` | No changes needed |

---

## 12. Mapping: Old Architecture → New Architecture

| Old Node | New Node | Notes |
|---|---|---|
| `goal_understanding` | `entity_extract` | Broader — extracts all entities, not just goal |
| `goal_decomposition` | `plan_proposal` | Produces directive, not sub-goals list |
| `objective_planner` | `react` | Dynamic tool selection, not hardcoded plan |
| `capability_dispatcher` | `tool_execution` | Executes one tool per ReAct step |
| `evidence_aggregator` | (removed) | Results go directly into `tool_observations` |
| `world_model` | (removed) | No separate world model — ReAct reasons over `tool_observations` |
| `goal_evaluator` | `reflect` | Richer evaluation criteria |
| `reflection` | `reflect` | Merged into single Reflect node |
| `critic` | `critic` (updated) | Now writes `critic_notes` instead of triggering replan |
| `explainability` | `relevant_response` | Merged — response generation includes reasoning |
| `human_approval` | `human_approval` (updated) | Same interrupt mechanism, adapted to new state |
| `action_dispatcher` | `tool_execution` | Tool dispatch now happens inside ReAct loop |
| `meta_reasoner` | (removed) | Recovery handled by ReAct reading `tool_observations` |
| `memory_update` | `relevant_response` | Memory written at response time |
| *(new)* | `intent_node` | New: Relevance gate + Path gate |
| *(new)* | `irrelevant_response` | New: Handles chitchat/off-topic |
| *(new)* | `negotiation_classification` | New: Information completeness check |
| *(new)* | `negotiation_question` | New: Dynamic follow-up question |
| *(new)* | `critic_gate` | New: Optional critic routing |

---

## 13. Implementation Risks and Conflicts

### Risk 1: `MemorySaver` State Shape Change
**Problem:** LangGraph's `MemorySaver` persists the full `TripState` dict. Changing the schema means existing in-memory sessions (during development) will have mismatched keys.  
**Mitigation:** Use `state.get(key, default)` consistently in all nodes. Clear the `MemorySaver` between test runs. For production: bump `thread_id` prefix or implement a state migration helper.

### Risk 2: Dual-Role `IntentNode`
**Problem:** The `IntentNode` acts as both a Relevance Gate and a Path Gate. Using the same node function for two roles requires reading `intent_gate_mode` from state and branching logic inside the node.  
**Mitigation:** The routing in `graph.py` controls which conditional edge applies after each `IntentNode` invocation. Alternatively, split into two separate node functions (`intent_relevance_gate` and `intent_path_gate`) registered as two separate nodes for cleaner code — this is the **recommended approach** during implementation.

### Risk 3: ReAct Loop Runaway
**Problem:** If `ReactNode` repeatedly decides `act` without making progress, `max_react_iterations` is the only guard.  
**Mitigation:** `max_react_iterations` is set conservatively to 8. The ReAct prompt explicitly instructs the model to respond/complete after repeated tool failures. `tool_observations` provides full context of what has been tried.

### Risk 4: `pending_tool_call` vs. `pending_tool_calls` (singular vs. plural)
**Problem:** The old `human_approval.py` reads `pending_tool_calls` (a list). The new ReAct outputs one tool call at a time (`pending_tool_call`, singular).  
**Mitigation:** Update `human_approval.py` to read `pending_tool_call` (singular) and wrap it in a list internally for `ApprovalAction` construction.

### Risk 5: Tracing System Compatibility
**Problem:** `app/tracing.py` uses `track_node_start` / `track_node_end` via the `_instrument_node` wrapper in `graph/graph.py`. This is fully compatible with the new nodes — no changes needed to `tracing.py` itself.  
**Mitigation:** The `_instrument_node` wrapper function in `graph/graph.py` is reused as-is for all new nodes.

### Risk 6: Streamlit UI Reads Old State Fields
**Problem:** `ui/streamlit_app.py` and components read old fields: `explanation`, `sub_goals`, `world_facts`, `booking_results`, `payment_results`, `approval_status`.  
**Mitigation:**
  - `explanation` → `response_metadata` (update `render_explanation`)
  - `sub_goals` → `planning_directive.required_decisions` (update `render_plan_view`)
  - `world_facts` → `tool_observations` (update `render_plan_view`)
  - `booking_results`, `payment_results`, `approval_status` → **preserved unchanged**

### Risk 7: Prompt YAML incompatibility
**Problem:** Old prompts referenced fields like `{sub_goals}`, `{world_facts}`, `{full_plan}` that no longer exist.  
**Mitigation:** All new nodes use new YAML prompts. Old prompts are deleted. `services/prompt_loader.py` is unchanged.

### Risk 8: `schemas/state_schema.py` Pydantic models
**Problem:** `ParsedGoal`, `SubGoal`, `PlannedAction`, `WorldFact`, `SubGoalStatus`, `GoalEvaluation` are no longer directly used by new nodes.  
**Mitigation:** Keep `schemas/state_schema.py` unchanged (backward compatible), but new nodes will define their own Pydantic models as needed (or inline dicts). Remove dependency on `ParsedGoal` / `SubGoal` from new nodes.

### Risk 9: `create_initial_state()` in `graph/planner_loop.py`
**Problem:** `create_initial_state()` initialises the old state schema. It is called from both `app/main.py` and `ui/streamlit_app.py`.  
**Mitigation:** Update `create_initial_state()` to return the new `TripState` schema. Both callers are then automatically updated.
