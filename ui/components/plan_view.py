import streamlit as st

def render_plan_view(state):
    """Visualizes sub-goals, world facts, and collected evidence."""
    if not state:
        return
        
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Sub-Goals")
        sub_goals = state.get("sub_goals", [])
        if not sub_goals:
            st.info("No sub-goals generated yet.")
        for sg in sub_goals:
            status = sg.get("status", "pending")
            icon = "⏳"
            if status == "completed": icon = "✅"
            elif status == "failed": icon = "❌"
            elif status == "in_progress": icon = "🔄"
            
            st.markdown(f"{icon} **{sg.get('category', '').title()}**: {sg.get('description', '')}")

    with col2:
        st.markdown("### World Facts")
        facts = state.get("world_facts", [])
        if not facts:
            st.info("No facts derived yet.")
        for fact in facts:
            confidence = fact.get("confidence", 0)
            st.caption(f"[{confidence:.0%} confidence]")
            st.write(f"- {fact.get('statement')}")
            
    st.divider()
    st.markdown("### Raw Evidence Collected")
    evidence = state.get("evidence", {})
    if not evidence:
        st.info("No evidence collected yet.")
    else:
        st.json(evidence)
