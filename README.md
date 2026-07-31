# AtlasAI

An autonomous, goal-driven travel planning agent built with LangGraph, LangChain, and Streamlit.

AtlasAI doesn't follow a rigid workflow. Instead, it continuously reasons about the user's overarching goal, decomposes it into manageable sub-goals, dispatches specialised tools, reflects on its own plans, and recovers gracefully from failures.

## Features

- **Goal-Driven Architecture:** Dynamically decomposes complex requests into prioritized sub-goals.
- **Continuous Loop:** Plans, executes, gathers evidence, builds a world model, and evaluates until goals are satisfied.
- **Reflection & Critic (Phase 2):** Self-evaluates plans for gaps, forgotten considerations, and logical errors before finalising.
- **Explainability:** Provides transparent reasoning for every decision made.
- **Human-in-the-Loop (Phase 3):** Pauses execution to seek human approval before performing irreversible actions like booking or payments.
- **Meta-Reasoning & Failure Recovery (Phase 3):** Diagnoses tool failures or rejections and formulates optimal recovery strategies (retry, alternative, replan, escalate).
- **Memory Subsystem (Phase 3):** Uses ChromaDB for semantic user preferences and episodic session memory, plus JSON for tool performance tracking.
- **Multi-Agent Skeleton (Phase 3):** Includes a `CoordinatorAgent` and specialized agents (`TravelPlanner`, `BudgetAnalyst`, `LocalExpert`, `BookingSpecialist`) ready for localized task delegation.
- **Interactive UI:** Streamlit interface with chat, plan visualization, execution traces, approval cards, and sidebars.

## Setup

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and set your API keys (OpenAI or Anthropic).

## Running the App

Start the Streamlit UI:
```bash
streamlit run ui/streamlit_app.py
```

## Running Tests

Execute the comprehensive test suite:
```bash
pytest tests/ -v
```

## Architecture

1. **Goal Understanding:** Parses raw input into a structured goal.
2. **Goal Decomposition:** Breaks the goal into prioritized sub-goals with dependencies.
3. **Objective Planner:** Generates the next best action(s).
4. **Capability Dispatcher:** Executes tools and collects results.
5. **Evidence Aggregator:** Consolidates raw tool results into structured evidence.
6. **World Model:** Extracts high-confidence facts and implications.
7. **Goal Evaluator:** Checks if all sub-goals are met.
8. **Reflection & Critic:** QA layer to catch oversights and critique the plan.
9. **Explainability:** Generates user-friendly explanations for choices.
10. **Human Approval:** LangGraph interrupt mechanism for irreversible actions.
11. **Action Dispatcher:** Executes confirmed bookings/payments.
12. **Meta Reasoner:** Handles errors and formulates recovery strategies.
13. **Memory Update:** Persists learned preferences and episodic summaries to ChromaDB.

## Multi-Agent Skeleton

Phase 3 introduces a multi-agent skeleton. The `CoordinatorAgent` currently delegates to the main planner loop but is structured to eventually dispatch specialized agents for specific tasks.
