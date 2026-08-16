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
    train_number: str = "82501",
    date: str = "2026-08-20",
    passengers: list | None = None,
    travel_class: str = "CC",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute authenticated train booking via RailwayBookingProvider."""
    cap = check_booking_capability("train")
    if not cap.get("available", False):
        reason = cap.get("reason", "Railway booking capability unavailable.")
        logger.error("book_train: execution blocked — %s", reason)
        raise RuntimeError(f"Booking execution unavailable: {reason}")

    train_id = train_number or kwargs.get("train_id", "82501")
    journey_date = date or kwargs.get("journey_date", "2026-08-20")
    pax_list = passengers or kwargs.get("passenger_info", [{"name": "Default Traveler"}])
    class_type = travel_class or kwargs.get("class_type", "CC")

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
    flight_number: str = "6E252",
    date: str = "2026-08-20",
    passengers: list | None = None,
    seat_preference: str = "window",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute authenticated flight booking via FlightBookingProvider."""
    cap = check_booking_capability("flight")
    if not cap.get("available", False):
        reason = cap.get("reason", "Flight booking capability unavailable.")
        logger.error("book_flight: execution blocked — %s", reason)
        raise RuntimeError(f"Booking execution unavailable: {reason}")

    flt_no = flight_number or kwargs.get("flight_id", "6E252")
    flt_date = date or kwargs.get("travel_date", "2026-08-20")
    pax_list = passengers or kwargs.get("passenger_info", [{"name": "Default Traveler"}])

    provider = FlightBookingProvider()
    result = provider.execute_booking(
        flight_number=flt_no,
        date=flt_date,
        passengers=pax_list,
        seat_preference=seat_preference,
        **kwargs,
    )
    return result


def book_hotel(
    hotel_name: str = "Grand Hotel",
    checkin_date: str = "2026-08-20",
    checkout_date: str = "2026-08-23",
    guest_info: dict | None = None,
    room_type: str = "deluxe",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Execute authenticated hotel booking via HotelBookingProvider."""
    cap = check_booking_capability("hotel")
    if not cap.get("available", False):
        reason = cap.get("reason", "Hotel booking capability unavailable.")
        logger.error("book_hotel: execution blocked — %s", reason)
        raise RuntimeError(f"Booking execution unavailable: {reason}")

    h_name = hotel_name or kwargs.get("name", "Grand Hotel")
    c_in = checkin_date or kwargs.get("checkin", "2026-08-20")
    c_out = checkout_date or kwargs.get("checkout", "2026-08-23")
    g_info = guest_info or kwargs.get("guest", {"name": "Default Guest"})

    provider = HotelBookingProvider()
    result = provider.execute_booking(
        hotel_name=h_name,
        checkin_date=c_in,
        checkout_date=c_out,
        guest_info=g_info,
        room_type=room_type,
        **kwargs,
    )
    return result


# Function aliases for canonical tool names
flight_booking = book_flight
hotel_booking = book_hotel
train_booking = book_train
