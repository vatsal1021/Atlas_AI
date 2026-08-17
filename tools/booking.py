"""Booking Execution Tools.

Integrates with authenticated providers (RailwayBookingProvider, FlightBookingProvider, HotelBookingProvider)
to execute real/simulated bookings upon validation and HITL approval.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from services.booking.capability import check_booking_capability
from services.booking.providers.railway_provider import RailwayBookingProvider
from services.booking.providers.flight_provider import FlightBookingProvider
from services.booking.providers.hotel_provider import HotelBookingProvider
from schemas.approval_schema import BookingConfirmation

logger = logging.getLogger(__name__)


def book_train(
    train_number: str | None = None,
    date: str | None = None,
    passengers: list | None = None,
    travel_class: str | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute authenticated train booking via RailwayBookingProvider."""
    cap = check_booking_capability("train")
    if not cap.get("available", False):
        reason = cap.get("reason", "Railway booking capability unavailable.")
        logger.error("book_train: execution blocked — %s", reason)
        raise RuntimeError(f"Booking execution unavailable: {reason}")

    train_id = train_number or kwargs.get("train_id")
    journey_date = date or kwargs.get("journey_date") or kwargs.get("date")
    pax_list = passengers or kwargs.get("passenger_info")
    class_type = travel_class or kwargs.get("class_type") or "CC"

    if not train_id:
        raise ValueError("Tool execution failed: missing required parameter 'train_number'. Please provide the train details and retry.")
    if not journey_date:
        raise ValueError("Tool execution failed: missing required parameter 'date'. Please provide the journey date and retry.")
    if not pax_list or not isinstance(pax_list, list) or len(pax_list) == 0:
        raise ValueError("Tool execution failed: missing required parameter 'passengers'. Please provide passenger details and retry.")

    provider = RailwayBookingProvider()
    result = provider.execute_booking(
        train_id=train_id,
        journey_date=journey_date,
        passengers=pax_list,
        class_type=class_type,
        **kwargs,
    )
    return result


def book_flight(
    flight_number: str | None = None,
    date: str | None = None,
    passengers: list | None = None,
    seat_preference: str | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute authenticated flight booking via FlightBookingProvider."""
    cap = check_booking_capability("flight")
    if not cap.get("available", False):
        reason = cap.get("reason", "Flight booking capability unavailable.")
        logger.error("book_flight: execution blocked — %s", reason)
        raise RuntimeError(f"Booking execution unavailable: {reason}")

    flt_no = flight_number or kwargs.get("flight_id")
    flt_date = date or kwargs.get("travel_date") or kwargs.get("date")
    pax_list = passengers or kwargs.get("passenger_info")
    seat_pref = seat_preference or kwargs.get("seat_pref") or "window"

    if not flt_no:
        raise ValueError("Tool execution failed: missing required parameter 'flight_number'. Please provide the flight details and retry.")
    if not flt_date:
        raise ValueError("Tool execution failed: missing required parameter 'date'. Please provide the travel date and retry.")
    if not pax_list or not isinstance(pax_list, list) or len(pax_list) == 0:
        raise ValueError("Tool execution failed: missing required parameter 'passengers'. Please provide passenger details and retry.")

    provider = FlightBookingProvider()
    result = provider.execute_booking(
        flight_number=flt_no,
        date=flt_date,
        passengers=pax_list,
        seat_preference=seat_pref,
        **kwargs,
    )
    return result


def book_hotel(
    hotel_name: str | None = None,
    checkin_date: str | None = None,
    checkout_date: str | None = None,
    guest_info: dict | None = None,
    room_type: str | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute authenticated hotel booking via HotelBookingProvider."""
    cap = check_booking_capability("hotel")
    if not cap.get("available", False):
        reason = cap.get("reason", "Hotel booking capability unavailable.")
        logger.error("book_hotel: execution blocked — %s", reason)
        raise RuntimeError(f"Booking execution unavailable: {reason}")

    h_name = hotel_name or kwargs.get("name")
    c_in = checkin_date or kwargs.get("checkin") or kwargs.get("start_date")
    c_out = checkout_date or kwargs.get("checkout") or kwargs.get("end_date")
    g_info = guest_info or kwargs.get("guest")
    rm_type = room_type or kwargs.get("room") or "Deluxe Room"

    if not h_name:
        raise ValueError("Tool execution failed: missing required parameter 'hotel_name'. Please provide the hotel name and retry.")
    if not c_in:
        raise ValueError("Tool execution failed: missing required parameter 'checkin_date'. Please provide the check-in date and retry.")
    if not c_out:
        raise ValueError("Tool execution failed: missing required parameter 'checkout_date'. Please provide the check-out date and retry.")
    if not g_info or not isinstance(g_info, dict):
        raise ValueError("Tool execution failed: missing required parameter 'guest_info'. Please provide guest details and retry.")

    provider = HotelBookingProvider()
    result = provider.execute_booking(
        hotel_name=h_name,
        checkin_date=c_in,
        checkout_date=c_out,
        guest_info=g_info,
        room_type=rm_type,
        **kwargs,
    )
    return result
