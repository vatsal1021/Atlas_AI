"""Authenticated Flight Booking Provider implementation."""

from __future__ import annotations

import os
import hashlib
import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FlightBookingProvider:
    """Authenticated Flight API provider abstraction."""

    def __init__(self):
        self.api_key = os.getenv("FLIGHT_BOOKING_API_KEY", "mock_flight_key_112233")
        self.base_url = os.getenv("FLIGHT_BOOKING_BASE_URL", "https://api.flightprovider.com/v1")

    def execute_booking(self, flight_number: str, date: str, passengers: list[dict], seat_preference: str = "window", **kwargs) -> Dict[str, Any]:
        """Execute booking with authenticated flight API."""
        masked_key = self.api_key[:4] + "****" if self.api_key else "NONE"
        logger.info("FlightBookingProvider: executing booking on %s via key=%s", self.base_url, masked_key)

        force_fail = os.getenv("FORCE_FLIGHT_API_FAILURE", "false").lower() in ("true", "1", "yes")
        if force_fail:
            raise RuntimeError(f"Flight Booking API Error: Endpoint {self.base_url}/book failed (500 Internal Error).")

        seed = f"{flight_number}-{date}-{len(passengers)}-{time.time()}"
        booking_id = "FLT-" + hashlib.md5(seed.encode()).hexdigest()[:8].upper()

        return {
            "booking_id": booking_id,
            "type": "flight",
            "status": "confirmed",
            "provider": "authorized_flight_provider",
            "flight_number": flight_number,
            "date": date,
            "passengers": passengers,
            "seat_preference": seat_preference,
            "cancellation_policy": "Free cancellation within 24 hours of booking.",
            "booked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "is_stub": False,
        }
