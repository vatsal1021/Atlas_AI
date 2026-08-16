"""RelevantResponseNode — Final response generator for all travel requests.

Reads planning_directive, tool_observations, react_reasoning_log,
extracted_entities, critic_notes, and reflect_feedback to generate a
single comprehensive response including answer, reasoning, recommendations,
risks, and warnings.

Also updates conversation_history and session_summary before END.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import TripState
from services.llm import get_llm
from services.prompt_loader import load_prompt
from app.tracing import get_tracker

logger = logging.getLogger(__name__)


def relevant_response(state: TripState) -> dict[str, Any]:
    """Generate the final comprehensive travel response."""
    tracker = get_tracker()

    directive = state.get("planning_directive", {})
    extracted = state.get("extracted_entities", {})
    observations = state.get("tool_observations", [])
    reasoning_log = state.get("react_reasoning_log", [])
    critic_notes = state.get("critic_notes", [])
    reflect_feedback = state.get("reflect_feedback", "")
    user_input = state.get("user_input", "")
    history = state.get("conversation_history", [])
    booking_results = state.get("booking_results", [])
    payment_results = state.get("payment_results", [])

    system_prompt, user_template = load_prompt("relevant_response")
    user_content = user_template.format(
        user_input=user_input,
        planning_directive=json.dumps(directive, indent=2) if directive else "None",
        extracted_entities=json.dumps(extracted, indent=2),
        tool_observations=_format_observations(observations),
        react_reasoning_log="\n".join(reasoning_log) if reasoning_log else "None",
        critic_notes=json.dumps(critic_notes) if critic_notes else "None",
        reflect_feedback=reflect_feedback or "None",
        booking_results=json.dumps(booking_results) if booking_results else "None",
        payment_results=json.dumps(payment_results) if payment_results else "None",
    )

    booking_flow_active = state.get("booking_flow_active", False)
    req_complete = state.get("booking_requirements_complete", False)
    missing_fields = state.get("missing_booking_fields", [])
    cap_available = state.get("booking_capability_available", False)
    selected = state.get("selected_booking", {})
    passengers = state.get("passenger_info", [])

    # If in active booking flow, format structured clean responses
    if booking_flow_active and not req_complete and missing_fields:
        item_desc = ""
        if selected.get("train_name"):
            item_desc = f"{selected.get('train_name')} ({selected.get('train_number', '')}), departing {selected.get('origin', 'origin')} at {selected.get('departure_time', 'departure')} on {selected.get('date', '')}"
        elif selected.get("flight_number"):
            item_desc = f"Flight {selected.get('flight_number')} on {selected.get('date', '')}"
        elif selected.get("hotel_name"):
            item_desc = f"{selected.get('hotel_name')}"
        else:
            item_desc = "your selected option"

        field_labels = {
            "passenger.name": "Full name",
            "passenger.age": "Age",
            "passenger.gender": "Gender",
            "passenger.berth_preference": "Berth preference",
            "passenger.class": "Travel class (e.g. CC, 3A, 2A, 1A)",
            "passenger.seat_preference": "Seat preference",
            "passenger.passport_or_id": "Passport / ID number",
            "guest.name": "Full guest name",
            "guest.contact_email_or_phone": "Contact email or phone",
            "guest.checkin_date": "Check-in date",
            "guest.checkout_date": "Check-out date",
            "guest.room_type": "Room type",
        }

        missing_list = "\n".join([f"- {field_labels.get(f, f)}" for f in missing_fields])

        reply = (
            f"Great, you've selected **{item_desc}**.\n\n"
            f"Before I can proceed with the booking, I need the passenger details required for the ticket.\n\n"
            f"Please provide:\n{missing_list}"
        )
    elif booking_flow_active and req_complete and not cap_available:
        item_desc = selected.get("train_name", "the selected option")
        if selected.get("train_number"):
            item_desc += f" ({selected.get('train_number')})"

        reply = (
            f"I have collected all the required passenger information for **{item_desc}**, "
            f"but this system currently does not have an authenticated railway booking provider configured, "
            f"so I cannot execute the live booking."
        )
    else:
        llm = get_llm(temperature=0.5)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ])
        reply = response.content.strip()  # type: ignore[union-attr]

    # Build structured metadata for UI
    response_metadata = {
        "tool_observations_count": len(observations),
        "tools_used": list({obs.get("tool") for obs in observations if obs.get("tool")}),
        "react_steps": len(reasoning_log),
        "critic_ran": bool(critic_notes),
        "critic_notes": critic_notes,
        "booking_results": booking_results,
        "payment_results": payment_results,
    }

    # Update conversation history
    conv_history = list(history)
    if user_input:
        conv_history.append({"role": "user", "content": user_input})
    conv_history.append({"role": "assistant", "content": reply})

    # Session summary
    session_summary = {
        "last_response_length": len(reply),
        "tools_used": response_metadata["tools_used"],
        "react_steps": response_metadata["react_steps"],
    }

    logger.info(
        "relevant_response: response_len=%d  tools_used=%s",
        len(reply),
        response_metadata["tools_used"],
    )
    if tracker:
        tracker.log_trace(
            f"[RelevantResponseNode] Generated response ({len(reply)} chars)"
        )

    return {
        "final_response": reply,
        "response_metadata": response_metadata,
        "conversation_history": conv_history,
        "session_summary": session_summary,
    }


def _format_observations(observations: list[dict]) -> str:
    if not observations:
        return "No tool results (zero-tool plan — response generated from knowledge)."
    lines = []
    for obs in observations:
        tool = obs.get("tool", "?")
        status = obs.get("status", "?")
        result = json.dumps(obs.get("result", {}), default=str)
        if len(result) > 500:
            result = result[:497] + "..."
        lines.append(f"  [{status.upper()}] {tool}:\n    {result}")
    return "\n".join(lines)
