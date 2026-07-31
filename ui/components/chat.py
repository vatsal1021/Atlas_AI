import streamlit as st

def render_chat(messages, current_node):
    """Renders the chat interface and the live status of the agent."""
    st.markdown("### Agent Progress")
    
    # Display message history
    for msg in messages:
        role = msg.get("role", "system")
        with st.chat_message(role):
            st.write(msg.get("content", ""))

    # Display live status if planning is active
    if current_node:
        with st.status(f"Agent is working... (Current step: {current_node})", expanded=True):
            st.write("Generating sub-goals, gathering evidence, and analyzing...")
