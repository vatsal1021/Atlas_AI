import streamlit as st

def render_explanation(explanation_dict):
    """Renders the structured explanation, risks, and tradeoffs."""
    if not explanation_dict:
        st.info("Explanation will appear here once the plan is finalized.")
        return

    st.markdown("## 🧠 Why we chose this plan")
    
    # Decisions
    decisions = explanation_dict.get("decisions", [])
    if decisions:
        st.markdown("### Key Decisions")
        for decision in decisions:
            with st.expander(decision.get("item", "Decision")):
                st.write(f"**Reasoning:** {decision.get('reasoning', '')}")
                cols = st.columns(2)
                with cols[0]:
                    st.markdown("**Pros**")
                    for pro in decision.get("pros", []):
                        st.write(f"🟢 {pro}")
                with cols[1]:
                    st.markdown("**Cons**")
                    for con in decision.get("cons", []):
                        st.write(f"🔴 {con}")

    st.divider()
    
    # Risks and Tradeoffs
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚠️ Risks & Mitigations")
        risks = explanation_dict.get("risks", [])
        for r in risks:
            st.warning(f"**Risk:** {r.get('risk')}\n\n**Mitigation:** {r.get('mitigation')}")
            
    with col2:
        st.markdown("### ⚖️ Tradeoffs & Alternatives")
        tradeoffs = explanation_dict.get("tradeoffs", [])
        for t in tradeoffs:
            st.info(f"**Tradeoff:** {t}")
            
        alternatives = explanation_dict.get("alternatives", [])
        if alternatives:
            st.markdown("**Considered but rejected:**")
            for alt in alternatives:
                st.caption(f"- {alt}")
