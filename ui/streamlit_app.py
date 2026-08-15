"""Main Streamlit app entrypoint for AtlasAI — new architecture."""

import sys
import os

# Ensure the root directory is in sys.path so we can import 'app', 'graph', etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from langgraph.types import Command

from app.config import configure_logging, get_settings
from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
from app.tracing import start_execution_tracker

from ui.components.chat import render_chat
from ui.components.plan_view import render_plan_view
from ui.components.explanation_panel import render_explanation
from ui.components.approval_card import render_approval_card
from ui.components.sidebar import render_sidebar

configure_logging()

_AFFIRMATIVE_TERMS = {
    "yes", "yeah", "yea", "yep", "yup", "sure", "ok", "okay", "go ahead",
    "proceed", "do it", "confirm", "approve", "book it", "book", "fine",
    "agree", "move ahead", "finalize", "please book", "go for it",
}

_NEGATIVE_TERMS = {
    "no", "nope", "dont", "don't", "cancel", "stop", "reject", "decline",
    "nevermind", "never mind", "abort",
}


def _check_approval_intent(text: str) -> tuple[bool, bool]:
    """Classify natural language text for approval or rejection intent."""
    clean = text.lower().strip()
    is_yes = any(term in clean for term in _AFFIRMATIVE_TERMS)
    is_no = any(term in clean for term in _NEGATIVE_TERMS)
    return is_yes, is_no


# ── Helpers (must be defined before use in module-level code) ─────────────────

def _node_label(node_name: str) -> str:
    """Convert internal node names to friendly display labels."""
    labels = {
        "intent_node":               "Classifying your request...",
        "irrelevant_response":       "Generating response...",
        "entity_extract":            "Understanding your request...",
        "negotiation_classification":"Checking if I need more info...",
        "negotiation_question":      "Preparing a follow-up question...",
        "path_gate_setter":          "Determining approach...",
        "plan_proposal":             "Creating a planning strategy...",
        "react":                     "Reasoning about next steps...",
        "tool_execution":            "Gathering travel data...",
        "human_approval":            "Waiting for your approval...",
        "reflect":                   "Reviewing the plan quality...",
        "critic_gate":               "Assessing plan complexity...",
        "critic":                    "Running quality check...",
        "relevant_response":         "Writing your travel plan...",
    }
    return labels.get(node_name, f"Running {node_name}...")


def _already_shown(messages: list[dict], content: str) -> bool:
    """Check if a message is already in the chat history."""
    return any(m.get("content") == content for m in messages)


# ── Session State Init ────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "session_1"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph" not in st.session_state:
    st.session_state.graph = compile_graph()
if "trip_state" not in st.session_state:
    st.session_state.trip_state = None
if "resume_command" not in st.session_state:
    st.session_state.resume_command = None

config = {"configurable": {"thread_id": st.session_state.thread_id}}

st.set_page_config(page_title="AtlasAI Planner", page_icon="🌍", layout="wide")
st.title("🌍 AtlasAI")
st.caption("Your AI Travel Planning Companion")

col_chat, col_plan = st.columns([1, 1.5])

with col_chat:
    # ── Chat Input ────────────────────────────────────────────────────────
    prompt = st.chat_input("Ask me anything about your trip...")

    # Render existing chat history
    render_chat(st.session_state.messages, current_node=None)

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Check if the graph is currently in an interrupted state awaiting approval
        active_checkpoint = st.session_state.graph.get_state(config)
        if active_checkpoint and active_checkpoint.next:
            is_yes, is_no = _check_approval_intent(prompt)
            if is_yes and not is_no:
                st.session_state.resume_command = Command(resume={"approved": True, "reason": prompt})
            elif is_no:
                st.session_state.resume_command = Command(resume={"approved": False, "reason": prompt})
            else:
                st.session_state.resume_command = Command(resume={"approved": False, "reason": f"User input: {prompt}"})
        else:
            st.session_state.trip_state = None
            st.session_state.resume_command = None

        st.rerun()

# ── Graph Execution Logic ─────────────────────────────────────────────────────
should_run_graph = False
initial_state = None
user_request = ""

last_msg = st.session_state.messages[-1] if st.session_state.messages else None

if st.session_state.resume_command is not None:
    should_run_graph = True
    initial_state = st.session_state.resume_command  # Command object for resume
    st.session_state.resume_command = None

elif last_msg and last_msg["role"] == "user" and not st.session_state.trip_state:
    should_run_graph = True
    user_request = last_msg["content"]
    existing_checkpoint = st.session_state.graph.get_state(config)
    existing_values = existing_checkpoint.values if existing_checkpoint else None
    initial_state = create_initial_state(user_request, existing_state=existing_values)

if should_run_graph:
    with col_chat:
        status_placeholder = st.empty()
        node_log = []

        tracker = start_execution_tracker(
            run_id=st.session_state.thread_id,
            user_input=user_request or "Resuming from interrupt",
        )

        try:
            for event in st.session_state.graph.stream(initial_state, config=config):
                for node_name, state_update in event.items():
                    node_log.append(node_name)
                    friendly = _node_label(node_name)
                    status_placeholder.status(
                        f"⚙️ {friendly}",
                        expanded=False,
                    )
        except Exception as e:
            st.error(f"Graph execution error: {e}")
            tracker.track_workflow_complete(success=False, error=str(e))

        # Retrieve latest graph state
        current_state = st.session_state.graph.get_state(config)
        if current_state and current_state.values:
            st.session_state.trip_state = current_state.values

        # Show final_response as assistant message in chat
        if current_state and current_state.values:
            final_resp = current_state.values.get("final_response", "")
            if final_resp and not _already_shown(st.session_state.messages, final_resp):
                st.session_state.messages.append({"role": "assistant", "content": final_resp})

        # Check if paused for human approval
        if current_state and current_state.next:
            status_placeholder.empty()
            approval_msg = "I need your approval before proceeding."
            if current_state.tasks:
                for task in current_state.tasks:
                    if task.interrupts:
                        approval_msg = task.interrupts[0].value.get("message", approval_msg)
                        break
            if not _already_shown(st.session_state.messages, approval_msg):
                st.session_state.messages.append({"role": "assistant", "content": approval_msg})
            tracker.track_workflow_complete(success=True)
        else:
            status_placeholder.empty()
            tracker.track_workflow_complete(success=True)

        st.rerun()


# ── Right Panel ───────────────────────────────────────────────────────────────
state = st.session_state.trip_state
render_sidebar(state)

with col_plan:
    if state:
        tab_plan, tab_explain, tab_approve = st.tabs(
            ["🗺️ Plan Details", "🧠 Agent Insights", "🔒 Approval & Bookings"]
        )

        with tab_plan:
            render_plan_view(state)

        with tab_explain:
            render_explanation(state.get("response_metadata"))

        with tab_approve:
            render_approval_card(state, config=config, graph=st.session_state.graph)

            bookings = state.get("booking_results", [])
            payments = state.get("payment_results", [])
            if bookings or payments:
                st.divider()
                st.subheader("Confirmed Bookings")
