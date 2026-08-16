"""Booking Requirements Registry.

Defines required field schemas for different booking types (train, flight, hotel).
Extendable for provider-specific or domain-specific requirements.
"""

from __future__ import annotations

from typing import Dict, List

# Standard required fields per booking domain
TRAIN_REQUIREMENTS: List[str] = [
    "passenger.name",
    "passenger.age",
    "passenger.gender",
    "passenger.berth_preference",
    "passenger.class",
]

FLIGHT_REQUIREMENTS: List[str] = [
    "passenger.name",
    "passenger.dob_or_age",
    "passenger.gender",
    "passenger.passport_or_id",
    "passenger.seat_preference",
]

HOTEL_REQUIREMENTS: List[str] = [
    "guest.name",
    "guest.contact_email_or_phone",
    "guest.checkin_date",
    "guest.checkout_date",
    "guest.room_type",
]

BOOKING_REQUIREMENTS_REGISTRY: Dict[str, List[str]] = {
    "train": TRAIN_REQUIREMENTS,
    "flight": FLIGHT_REQUIREMENTS,
    "hotel": HOTEL_REQUIREMENTS,
}


def get_requirements_for_type(booking_type: str) -> List[str]:
    """Retrieve list of required field descriptors for a given booking type."""
    norm_type = booking_type.lower().strip()
    return BOOKING_REQUIREMENTS_REGISTRY.get(norm_type, [])
