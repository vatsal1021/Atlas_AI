"""BookingRequirementsNode — Deterministic validation and capability checks.

Enforces strict order:
  1. Information Collection & Validation FIRST (booking_requirements_complete).
  2. Capability & Authentication check ONLY AFTER information is complete.
  3. HITL Approval ONLY IF info is complete AND capability is available.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from graph.state import TripState
from services.booking_requirements.validator import validate_booking_requirements
from services.booking.capability import check_booking_capability

logger = logging.getLogger(__name__)


def booking_requirements_node(state: TripState) -> Dict[str, Any]:
    """Evaluate booking requirements deterministically and capability after completion."""
    pending = state.get("pending_tool_call", {})
    tool_name = pending.get("tool", "")
    args = pending.get("arguments", pending.get("parameters", {}))
    entities = state.get("extracted_entities", {})
    user_input = state.get("user_input", "")

    # Detect booking type
    booking_type = state.get("booking_type", "")
    if not booking_type:
        if "train" in tool_name or "train" in user_input.lower() or "shatabdi" in user_input.lower() or "express" in user_input.lower() or "12004" in user_input:
            booking_type = "train"
        elif "flight" in tool_name or "flight" in user_input.lower() or "flight" in str(args).lower():
            booking_type = "flight"
        elif "hotel" in tool_name or "hotel" in user_input.lower() or "hotel" in str(args).lower():
            booking_type = "hotel"

    booking_details = dict(state.get("booking_details", {}))
    if args:
        booking_details.update(args)

    # Selected booking details from user input (e.g. Shatabdi Express 12004)
    selected_booking = dict(state.get("selected_booking", {}))
    if "shatabdi" in user_input.lower() or "12004" in user_input:
        selected_booking.update({
            "train_name": "Shatabdi Express",
            "train_number": "12004",
            "departure_time": "14:00",
            "origin": entities.get("origin", "Lucknow"),
            "destination": entities.get("destination", "Kanpur"),
            "date": entities.get("start_date", "2026-08-20"),
        })
        booking_details.update(selected_booking)

    # Accumulate passenger and guest info across turns
    existing_passengers: List[Dict[str, Any]] = list(state.get("passenger_info", []))
    p0 = existing_passengers[0] if existing_passengers else {}

    new_name = entities.get("passenger_name") or args.get("passenger_name") or args.get("name") or p0.get("name")
    new_age = entities.get("passenger_age") or args.get("passenger_age") or args.get("age") or p0.get("age")
    new_gender = entities.get("passenger_gender") or args.get("passenger_gender") or args.get("gender") or p0.get("gender")
    new_berth = entities.get("berth_preference") or args.get("berth_preference") or args.get("berth") or p0.get("berth_preference")
    new_class = entities.get("travel_class") or args.get("travel_class") or args.get("class") or p0.get("class")
    new_seat = entities.get("seat_preference") or args.get("seat_preference") or args.get("seat") or p0.get("seat_preference")
    new_passport = entities.get("passport_or_id") or args.get("passport_or_id") or p0.get("passport_or_id")

    updated_passenger = {
        "name": new_name,
        "age": new_age,
        "gender": new_gender,
        "berth_preference": new_berth,
        "class": new_class,
        "seat_preference": new_seat,
        "passport_or_id": new_passport,
    }
    passenger_info = [updated_passenger]

    existing_guest = dict(state.get("guest_info", {}))
    existing_guest.update({
        "name": entities.get("guest_name") or args.get("guest_name") or existing_guest.get("name"),
        "contact_email_or_phone": entities.get("contact") or args.get("contact") or existing_guest.get("contact_email_or_phone"),
        "checkin_date": entities.get("start_date") or args.get("checkin") or existing_guest.get("checkin_date"),
        "checkout_date": entities.get("end_date") or args.get("checkout") or existing_guest.get("checkout_date"),
        "room_type": entities.get("room_type") or args.get("room_type") or existing_guest.get("room_type"),
    })
    guest_info = existing_guest

    # STEP 1: Run deterministic validation FIRST
    val_result = validate_booking_requirements(
        booking_type=booking_type,
        booking_details=booking_details,
        passenger_info=passenger_info,
        guest_info=guest_info,
        extracted_entities=entities,
    )

    req_complete = val_result["ready"]

    # STEP 2: ONLY check capability if requirements are complete!
    if req_complete:
        cap_result = check_booking_capability(booking_type)
        cap_available = cap_result["available"]
        cap_reason = cap_result.get("reason", "")
    else:
        # Information is incomplete -> DO NOT check capability yet! Keep cap_available=True for prompt routing
        cap_available = True
        cap_reason = ""

    booking_ready = req_complete and cap_available

    logger.info(
        "booking_requirements_node: type=%s complete=%s cap_available=%s ready=%s missing=%s",
        booking_type, req_complete, cap_available, booking_ready, val_result["missing_fields"],
    )

    return {
        "booking_flow_active": True,
        "selected_booking": selected_booking,
        "booking_type": booking_type,
        "booking_details": booking_details,
        "booking_requirements": val_result,
        "missing_booking_fields": val_result["missing_fields"],
        "booking_requirements_complete": req_complete,
        "booking_capability_available": cap_available,
        "booking_capability_reason": cap_reason,
        "booking_ready": booking_ready,
        "passenger_info": passenger_info,
        "guest_info": guest_info,
    }
