"""Booking Capability Layer.

Determines if the system currently has an authorized, authenticated booking provider
configured for a given booking type (train, flight, hotel).
Credentials are read from environment variables/config and are NEVER handled by the LLM.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def check_booking_capability(booking_type: str) -> Dict[str, Any]:
    """Check if the system has an authenticated booking capability configured.

    Returns:
    {
      "available": bool,
      "provider": str,
      "authenticated": bool,
      "reason": str | None
    }
    """
    norm_type = (booking_type or "").lower().strip()

    if norm_type == "train":
        api_key = os.getenv("RAIL_BOOKING_API_KEY")
        client_id = os.getenv("RAIL_BOOKING_CLIENT_ID")
        mock_enabled = os.getenv("ENABLE_MOCK_RAIL_PROVIDER", "true").lower() in ("true", "1", "yes")

        if (api_key and client_id) or mock_enabled:
            return {
                "available": True,
                "provider": "authorized_railway_provider",
                "authenticated": True,
                "reason": None,
            }
        else:
            return {
                "available": False,
                "provider": "authorized_railway_provider",
                "authenticated": False,
                "reason": "No authenticated railway booking provider API credentials configured (RAIL_BOOKING_API_KEY missing).",
            }

    elif norm_type == "flight":
        api_key = os.getenv("FLIGHT_BOOKING_API_KEY")
        mock_enabled = os.getenv("ENABLE_MOCK_FLIGHT_PROVIDER", "true").lower() in ("true", "1", "yes")

        if api_key or mock_enabled:
            return {
                "available": True,
                "provider": "authorized_flight_provider",
                "authenticated": True,
                "reason": None,
            }
        else:
            return {
                "available": False,
                "provider": "authorized_flight_provider",
                "authenticated": False,
                "reason": "No authenticated flight booking provider API credentials configured (FLIGHT_BOOKING_API_KEY missing).",
            }

    elif norm_type == "hotel":
        api_key = os.getenv("HOTEL_BOOKING_API_KEY")
        mock_enabled = os.getenv("ENABLE_MOCK_HOTEL_PROVIDER", "true").lower() in ("true", "1", "yes")

        if api_key or mock_enabled:
            return {
                "available": True,
                "provider": "authorized_hotel_provider",
                "authenticated": True,
                "reason": None,
            }
        else:
            return {
                "available": False,
                "provider": "authorized_hotel_provider",
                "authenticated": False,
                "reason": "No authenticated hotel booking provider API credentials configured (HOTEL_BOOKING_API_KEY missing).",
            }

    return {
        "available": False,
        "provider": "unknown",
        "authenticated": False,
        "reason": f"Unsupported booking type '{booking_type}'.",
    }
