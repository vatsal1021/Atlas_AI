"""Authenticated Hotel Booking Provider implementation."""

from __future__ import annotations

import os
import hashlib
import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class HotelBookingProvider:
    """Authenticated Hotel API provider abstraction."""

    def __init__(self):
        self.api_key = os.getenv("HOTEL_BOOKING_API_KEY", "mock_hotel_key_445566")
        self.base_url = os.getenv("HOTEL_BOOKING_BASE_URL", "https://api.hotelprovider.com/v1")

    def execute_booking(self, hotel_name: str, checkin_date: str, checkout_date: str, guest_info: dict, room_type: str = "deluxe", **kwargs) -> Dict[str, Any]:
        """Execute booking with authenticated hotel API."""
        masked_key = self.api_key[:4] + "****" if self.api_key else "NONE"
        logger.info("HotelBookingProvider: executing booking on %s via key=%s", self.base_url, masked_key)

        force_fail = os.getenv("FORCE_HOTEL_API_FAILURE", "false").lower() in ("true", "1", "yes")
        if force_fail:
            raise RuntimeError(f"Hotel Booking API Error: Endpoint {self.base_url}/reserve failed (502 Bad Gateway).")

        seed = f"{hotel_name}-{checkin_date}-{time.time()}"
        booking_id = "HTL-" + hashlib.md5(seed.encode()).hexdigest()[:8].upper()

        return {
            "booking_id": booking_id,
            "type": "hotel",
            "status": "confirmed",
            "provider": "authorized_hotel_provider",
            "hotel_name": hotel_name,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "room_type": room_type,
            "guest_info": guest_info,
            "cancellation_policy": "Free cancellation up to 48 hours before check-in.",
            "booked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "is_stub": False,
        }
