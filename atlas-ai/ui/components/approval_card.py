"""Approval card UI component."""

import streamlit as st
try:
    from langgraph.types import Command
except ImportError:
    Command = None

def render_approval_card(state: dict, config: dict = None, graph = None):
    """Render an interactive approval card for irreversible actions.
    
    In Phase 3, this integrates with LangGraph's interrupt() mechanism.
    """
    st.subheader("🔒 Action Approval Required")
    
    # Check if the graph is currently interrupted waiting for approval
    is_interrupted = False
    interrupt_data = None
    
    if graph and config:
        graph_state = graph.get_state(config)
        if graph_state and graph_state.next and graph_state.tasks:
            # Look for an interrupt in the tasks
            for task in graph_state.tasks:
                if task.interrupts:
                    is_interrupted = True
                    interrupt_data = task.interrupts[0].value
                    break
                    
    if not is_interrupted:
        status = state.get("approval_status", "")
        if status == "approved":
            st.success("Actions were approved.")
        elif status == "rejected":
            st.error(f"Actions were rejected. Reason: {state.get('approval_reason', '')}")
        elif status == "not_needed":
            st.info("No irreversible actions required approval.")
        else:
            st.info("No pending approvals.")
        return
        
    st.warning("⚠️ The agent has paused execution. It wants to perform irreversible actions.")
    
    actions = interrupt_data.get("actions", []) if interrupt_data else []
    if not actions:
        # Fallback to checking state if interrupt payload is empty
        pending = state.get("pending_tool_calls", [])
        irreversible_actions = {"book_flight", "book_hotel", "make_reservation", "process_payment"}
        actions = [c for c in pending if c.get("tool", "") in irreversible_actions]
        
    for action in actions:
        with st.expander(f"Action: {action.get('tool', 'Unknown')}", expanded=True):
            st.json(action.get("parameters", {}))
            if "reasoning" in action:
                st.caption(f"**Agent's Reason:** {action['reasoning']}")
                
    st.write("Do you approve these actions?")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("✅ Approve All", use_container_width=True, type="primary"):
            decision = {"approved": True, "reason": ""}
            if Command:
                st.session_state.resume_command = Command(resume=decision)
            st.rerun()
            
    with col2:
        reason = st.text_input("Reason for rejection (optional)", key="reject_reason")
        if st.button("❌ Reject", use_container_width=True):
            decision = {"approved": False, "reason": reason}
            if Command:
                st.session_state.resume_command = Command(resume=decision)
            st.rerun()
