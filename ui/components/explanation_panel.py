import streamlit as st


def render_explanation(response_metadata: dict | None):
    """Render agent insights from response_metadata and critic notes."""
    if not response_metadata:
        st.info("Agent insights will appear here once a plan is generated.")
        return

    st.markdown("## 🧠 Agent Insights")

    # ── Tools Used ────────────────────────────────────────────────────────
    tools_used = response_metadata.get("tools_used", [])
    react_steps = response_metadata.get("react_steps", 0)

    col1, col2, col3 = st.columns(3)
    col1.metric("Tools Called", len(tools_used))
    col2.metric("ReAct Steps", react_steps)
    col3.metric("Critic Ran", "Yes" if response_metadata.get("critic_ran") else "No")

    if tools_used:
        st.markdown("**Tools used this request:**")
        st.write(", ".join(f"`{t}`" for t in tools_used))

    st.divider()

    # ── Critic Notes ─────────────────────────────────────────────────────
    critic_notes = response_metadata.get("critic_notes", [])
    if critic_notes:
        st.markdown("### ⚠️ Critic Findings")
        for note in critic_notes:
            st.warning(note)
    else:
        st.success("✅ No critical issues found in this plan.")

    st.divider()

    # ── Booking & Payment Summary ─────────────────────────────────────────
    bookings = response_metadata.get("booking_results", [])
    payments = response_metadata.get("payment_results", [])

    if bookings:
        st.markdown("### 📋 Booking Summary")
        for b in bookings:
            st.success(
                f"✅ **{b.get('type', 'Booking').title()}** — ID: `{b.get('booking_id', 'N/A')}`"
            )

    if payments:
        st.markdown("### 💳 Payment Summary")
        for p in payments:
            st.success(
                f"💳 Paid **{p.get('amount')} {p.get('currency', 'INR')}** — "
                f"TXN: `{p.get('transaction_id', 'N/A')}`"
            )
