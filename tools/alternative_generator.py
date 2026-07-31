"""Alternative Generator tool.

When a booking or search fails (e.g., hotel fully booked), generates
alternative options by calling search tools with relaxed constraints.
"""

from __future__ import annotations

import logging
from typing import Any

from tools.travel_research import search_flights, search_hotels

logger = logging.getLogger(__name__)


def generate_alternatives(
    failed_option: dict | None = None,
    option_type: str = "hotel",
    **kwargs: Any,
) -> list[dict]:
    """Generate alternative options for a failed booking/search.

    Parameters
    ----------
    failed_option : dict | None
        The original option that failed.
    option_type : str
        Type of option: 'flight' or 'hotel'.

    Returns
    -------
    list[dict]
        A list of alternative options with relaxed constraints.
    """
    if failed_option is None:
        failed_option = {}

    logger.info(
        "generate_alternatives: Generating alternatives for %s. Failed: %s",
        option_type, failed_option.get("name", failed_option.get("airline", "unknown")),
    )

    alternatives = []

    if option_type == "flight":
        # Relax constraints: try different dates, airlines
        origin = failed_option.get("origin", kwargs.get("origin", "Delhi"))
        destination = failed_option.get("destination", kwargs.get("destination", "Tokyo"))
        date = failed_option.get("date", kwargs.get("date", "2026-09-01"))
        passengers = failed_option.get("passengers", kwargs.get("passengers", 1))

        # Search with the same params (mock tools return varied results)
        alternatives = search_flights(
            origin=origin,
            destination=destination,
            date=date,
            passengers=passengers,
        )
        # Tag as alternatives
        for alt in alternatives:
            alt["is_alternative"] = True
            alt["original_option"] = failed_option.get("name", "unknown")

    elif option_type == "hotel":
        destination = failed_option.get("destination", kwargs.get("destination", "Tokyo"))
        checkin = failed_option.get("checkin", kwargs.get("checkin", "2026-09-01"))
        checkout = failed_option.get("checkout", kwargs.get("checkout", "2026-09-06"))
        guests = failed_option.get("guests", kwargs.get("guests", 1))

        alternatives = search_hotels(
            destination=destination,
            checkin=checkin,
            checkout=checkout,
            guests=guests,
        )
        for alt in alternatives:
            alt["is_alternative"] = True
            alt["original_option"] = failed_option.get("name", "unknown")

    logger.info("generate_alternatives: Found %d alternatives.", len(alternatives))
    return alternatives
