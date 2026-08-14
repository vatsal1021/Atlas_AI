"""Sidebar component for AtlasAI Streamlit UI — new architecture."""

import streamlit as st


def render_sidebar(state: dict | None):
    """Render the sidebar with agent stats and reasoning trace."""
    with st.sidebar:
        st.header("📊 Agent Dashboard")

        if not state:
            st.info("Start a conversation to see live agent stats.")
            return

        # ── Intent & Path ─────────────────────────────────────────────────
        intent = state.get("intent_classification", "")
        path = state.get("path_decision", "")

        if intent:
            intent_color = "🟢" if intent == "relevant" else "🟡"
            st.markdown(f"**Intent:** {intent_color} `{intent}`")
        if path:
            st.markdown(f"**Path:** `{path}`")

        st.divider()

        # ── Metrics ───────────────────────────────────────────────────────
        st.subheader("📈 Execution Metrics")
        react_iter = state.get("react_iteration", 0)
        max_react = state.get("max_react_iterations", 8)
        reflect_iter = state.get("reflect_iteration", 0)
        tools_used = len(state.get("tool_observations", []))

        st.metric("ReAct Steps", f"{react_iter} / {max_react}")
        st.metric("Reflect Iterations", reflect_iter)
        st.metric("Tool Calls", tools_used)

        critic_decision = state.get("critic_gate_decision", "")
        if critic_decision:
            st.metric("Critic Gate", critic_decision.replace("_", " ").title())

        risk = state.get("critic_risk_level", "")
        if risk:
            risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
            st.markdown(f"**Risk Level:** {risk_icon} `{risk}`")

        if state.get("errors"):
            st.error(f"⚠️ {len(state['errors'])} error(s) encountered.")

        st.divider()

        # ── ReAct Reasoning Log ───────────────────────────────────────────
        reasoning_log = state.get("react_reasoning_log", [])
        st.subheader("🧠 ReAct Reasoning")
        with st.expander("View reasoning steps", expanded=False):
            if not reasoning_log:
                st.write("No reasoning logged yet.")
            else:
                for idx, step in enumerate(reasoning_log):
                    st.markdown(f"**Step {idx + 1}:**\n{step}")

        st.divider()

        # ── Negotiation Status ────────────────────────────────────────────
        neg_status = state.get("negotiation_status", "")
        if neg_status:
            st.subheader("💬 Negotiation")
            label = "✅ Information complete" if neg_status == "information_complete" else "⏳ Gathering information"
            st.info(label)
            missing = state.get("missing_fields", [])
            if missing:
                st.caption(f"Still needed: {', '.join(missing)}")

        st.divider()

        # ── Memory ────────────────────────────────────────────────────────
        st.subheader("💾 Memory")
        context = state.get("memory_context") or {}
        prefs = context.get("preferences_learned", [])
        if prefs:
            st.success(f"Learned {len(prefs)} user preference(s).")
            for p in prefs:
                st.caption(f"- {p}")
        else:
            st.write("No preferences learned yet.")
