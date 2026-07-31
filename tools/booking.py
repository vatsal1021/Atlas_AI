"""Booking tool stubs.

Mock implementations for flight and hotel booking.
Returns simulated booking confirmations.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def book_flight(**kwargs: Any) -> dict[str, Any]:
    """Book a flight (stub).

    Parameters
    ----------
    **kwargs
        Flight option details (airline, price, origin, destination, date, etc.)

    Returns
    -------
    dict
        A mock BookingConfirmation.
    """
    logger.warning("book_flight: STUB — no real booking is being made.")

    # Generate a deterministic booking ID from the input
    seed = str(sorted(kwargs.items()))
    booking_id = "FLT-" + hashlib.md5(seed.encode()).hexdigest()[:8].upper()

    return {
        "booking_id": booking_id,
        "type": "flight",
        "status": "confirmed",
        "details": kwargs,
        "cancellation_policy": "Free cancellation within 24 hours of booking.",
        "booked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "is_stub": True,
    }


def book_hotel(**kwargs: Any) -> dict[str, Any]:
    """Book a hotel (stub).

    Parameters
    ----------
    **kwargs
        Hotel option details (name, price_per_night, checkin, checkout, etc.)

    Returns
    -------
    dict
        A mock BookingConfirmation.
    """
    logger.warning("book_hotel: STUB — no real booking is being made.")

    seed = str(sorted(kwargs.items()))
    booking_id = "HTL-" + hashlib.md5(seed.encode()).hexdigest()[:8].upper()

    return {
        "booking_id": booking_id,
        "type": "hotel",
        "status": "confirmed",
        "details": kwargs,
        "cancellation_policy": "Free cancellation up to 48 hours before check-in.",
        "booked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "is_stub": True,
    }
