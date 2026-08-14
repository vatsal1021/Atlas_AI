import streamlit as st


def render_plan_view(state: dict | None):
    """Visualise planning directive, tool observations, and ReAct reasoning log."""
    if not state:
        return

    # ── Planning Directive ────────────────────────────────────────────────
    directive = state.get("planning_directive") or {}
    if directive:
        st.markdown("### 🎯 Planning Directive")
        if directive.get("objective"):
            st.info(f"**Objective:** {directive['objective']}")

        col1, col2 = st.columns(2)
        with col1:
            decisions = directive.get("required_decisions", [])
            if decisions:
                st.markdown("**Decisions to make:**")
                for d in decisions:
                    st.markdown(f"- {d}")
        with col2:
            criteria = directive.get("success_criteria", [])
            if criteria:
                st.markdown("**Success criteria:**")
                for c in criteria:
                    st.markdown(f"- ✅ {c}")

        constraints = directive.get("constraints", [])
        if constraints:
            st.markdown("**Constraints:**")
            for c in constraints:
                st.markdown(f"- ⚠️ {c}")

        st.divider()

    # ── Tool Observations ─────────────────────────────────────────────────
    observations = state.get("tool_observations", [])
    st.markdown("### 🔧 Tool Results")
    if not observations:
        st.info("No tools have been called yet for this request.")
    else:
        for obs in observations:
            tool = obs.get("tool", "unknown")
            status = obs.get("status", "unknown")
            icon = "✅" if status == "success" else "❌"
            with st.expander(f"{icon} `{tool}` — {status.upper()}"):
                if obs.get("arguments"):
                    st.caption("Arguments:")
                    st.json(obs["arguments"])
                if obs.get("result"):
                    st.caption("Result:")
                    st.json(obs["result"])
                if obs.get("error"):
                    st.error(obs["error"])

    st.divider()

    # ── ReAct Reasoning Log ───────────────────────────────────────────────
    reasoning_log = state.get("react_reasoning_log", [])
    if reasoning_log:
        st.markdown("### 🧠 ReAct Reasoning Steps")
        for idx, step in enumerate(reasoning_log):
            st.markdown(f"**Step {idx + 1}:** {step}")
