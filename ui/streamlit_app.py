"""Main Streamlit app entrypoint for AtlasAI."""

import sys
import os

# Ensure the root directory is in sys.path so we can import 'app', 'graph', etc.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from app.config import configure_logging, get_settings
from graph.graph import compile_graph
from graph.planner_loop import create_initial_state
from app.tracing import RuntimeTracer

from ui.components.chat import render_chat
from ui.components.plan_view import render_plan_view
from ui.components.explanation_panel import render_explanation
from ui.components.approval_card import render_approval_card
from ui.components.sidebar import render_sidebar

# Initialize app state
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

# Thread config for MemorySaver
config = {"configurable": {"thread_id": st.session_state.thread_id}}

st.set_page_config(page_title="AtlasAI Planner", page_icon="🌍", layout="wide")

st.title("🌍 AtlasAI")
st.caption("Autonomous, Goal-Driven Travel Planning Agent")

# Layout: Chat/Controls on Left, Visuals on Right
col_chat, col_plan = st.columns([1, 1.5])

with col_chat:
    prompt = st.chat_input("Where do you want to go?")
    
    # Render chat history
    render_chat(st.session_state.messages, current_node=None)
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Clear old state for new request
        st.session_state.trip_state = None
        st.session_state.resume_command = None
        st.rerun()

# Processing logic (handles both initial runs and resuming from interrupt)
should_run_graph = False
initial_state = None

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user" and not st.session_state.trip_state:
    should_run_graph = True
    user_request = st.session_state.messages[-1]["content"]
    settings = get_settings()
    initial_state = create_initial_state(user_request, max_iterations=settings.max_planner_iterations)
    
elif st.session_state.resume_command is not None:
    should_run_graph = True
    initial_state = st.session_state.resume_command  # Pass the Command object
    st.session_state.resume_command = None

if should_run_graph:
    with col_chat:
        status_container = st.status("Agent is planning...", expanded=True)
        
        # Initialize Tracer for this run
        tracer = RuntimeTracer(run_id=st.session_state.thread_id)
        config["callbacks"] = [tracer]
        tracer.log(f"User Request: {user_request}" if "user_request" in locals() else "Resuming from interrupt")
        
        # Run or resume the graph
        try:
            for event in st.session_state.graph.stream(initial_state, config=config):
                for node_name, state_update in event.items():
                    status_container.write(f"Executed node: **`{node_name}`**")
                    if isinstance(state_update, dict):
                        # Merge state updates locally if needed, but get_state is safer
                        pass
        except Exception as e:
            st.error(f"Graph execution error: {e}")
            
        # Update session state with the latest graph state
        current_state = st.session_state.graph.get_state(config)
        if current_state and current_state.values:
            st.session_state.trip_state = current_state.values
            
        # Check if we hit an interrupt
        if current_state and current_state.next:
            status_container.update(label="Paused for Approval!", state="error", expanded=True)
            
            # Extract dynamic message if available
            msg = "I need your approval before proceeding."
            if current_state.tasks:
                for task in current_state.tasks:
                    if task.interrupts:
                        msg = task.interrupts[0].value.get("message", msg)
                        break
                        
            st.session_state.messages.append({"role": "assistant", "content": msg})
            if "tracer" in locals():
                tracer.log(f"\\n[EVENT: SYSTEM] {msg}")
        else:
            status_container.update(label="Execution Complete!", state="complete", expanded=False)
            # Only add completion message if not already done
            if not any(m["content"] == "I've finished drafting your plan. Please review the details!" for m in st.session_state.messages):
                msg = "I've finished drafting your plan. Please review the details!"
                st.session_state.messages.append({"role": "assistant", "content": msg})
                if "tracer" in locals():
                    tracer.log(f"\\n[EVENT: SYSTEM] {msg}")
                
        st.rerun()

# Render visual plan state and Sidebar
state = st.session_state.trip_state
render_sidebar(state)

with col_plan:
    if state:
        tab_plan, tab_explain, tab_approve = st.tabs(["🗺️ The Plan", "🧠 Explainability", "🔒 Approval & Bookings"])
        
        with tab_plan:
            render_plan_view(state)
            
        with tab_explain:
            render_explanation(state.get("explanation"))
            
        with tab_approve:
            render_approval_card(state, config=config, graph=st.session_state.graph)
            
            # Show booking results if any
            bookings = state.get("booking_results", [])
            payments = state.get("payment_results", [])
            if bookings or payments:
                st.divider()
                st.subheader("Confirmed Bookings")
                for b in bookings:
                    st.success(f"✅ {b.get('type', 'Booking').title()} Confirmed: {b.get('booking_id')}")
                for p in payments:
                    st.success(f"💳 Payment Processed: {p.get('transaction_id')} ({p.get('amount')} {p.get('currency')})")
    else:
        st.info("Enter a destination to begin planning.")
