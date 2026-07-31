"""Sidebar component for AtlasAI Streamlit UI."""

import streamlit as st

def render_sidebar(state: dict | None):
    """Render the sidebar with agent stats and reasoning trace."""
    with st.sidebar:
        st.header("📊 Agent Dashboard")
        
        if not state:
            st.info("Start planning to see stats.")
            return
            
        st.subheader("Progress")
        st.metric("Planner Iterations", state.get("planner_iteration", 0), state.get("max_iterations", 10))
        st.metric("Sub-goals Generated", len(state.get("sub_goals", [])))
        st.metric("Recovery Attempts", state.get("recovery_attempts", 0))
        
        if state.get("errors"):
            st.error(f"Encountered {len(state.get('errors'))} error(s).")
            
        st.divider()
        
        st.subheader("🧠 Agent Reasoning")
        with st.expander("View Chain of Thought", expanded=False):
            reasoning = state.get("planner_reasoning", [])
            if not reasoning:
                st.write("No reasoning logged yet.")
            else:
                for idx, r in enumerate(reasoning):
                    st.markdown(f"**Step {idx+1}:**\n{r}")
                    
        st.divider()
        
        st.subheader("💾 Memory Subsystem")
        context = state.get("memory_context", {})
        prefs = context.get("preferences_learned", [])
        if prefs:
            st.success(f"Learned {len(prefs)} new preference(s).")
            for p in prefs:
                st.caption(f"- {p}")
        else:
            st.write("No new preferences learned yet.")
