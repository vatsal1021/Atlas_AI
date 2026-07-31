"""Travel research tools — mock/stub implementations for Phase 1.

Returns realistic fake flight and hotel data for any destination.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

from schemas.tool_schema import FlightOption, HotelOption

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock data pools
# ---------------------------------------------------------------------------
_AIRLINES = [
    ("Air India", "AI"), ("IndiGo", "6E"), ("SpiceJet", "SG"),
    ("Vistara", "UK"), ("ANA", "NH"), ("Japan Airlines", "JL"),
    ("Emirates", "EK"), ("Singapore Airlines", "SQ"), ("Thai Airways", "TG"),
    ("Lufthansa", "LH"), ("British Airways", "BA"),
]

_HOTEL_NAMES = [
    "Grand Hyatt", "Marriott Courtyard", "Hotel Sakura", "The Leela Palace",
    "Taj Resort", "Hilton Garden Inn", "Novotel City Centre",
    "Radisson Blu", "ITC Grand", "JW Marriott", "Holiday Inn Express",
    "Ritz-Carlton", "Four Seasons", "Oberoi",
]

_AMENITIES_POOL = [
    "Free WiFi", "Swimming Pool", "Spa", "Gym", "Restaurant",
    "Airport Shuttle", "Room Service", "Bar", "Parking",
    "Breakfast Included", "Laundry", "Business Centre",
]


def search_flights(
    origin: str,
    destination: str,
    date: str,
    passengers: int = 1,
) -> list[dict]:
    """Return mock flight options.

    Parameters
    ----------
    origin : str
        Origin city/airport code.
    destination : str
        Destination city/airport code.
    date : str
        Departure date ISO string.
    passengers : int
        Number of passengers.

    Returns
    -------
    list[dict]
        Serialised FlightOption dicts.
    """
    logger.info(
        "search_flights  origin=%s  dest=%s  date=%s  pax=%s",
        origin, destination, date, passengers,
    )
    rng = random.Random(f"{origin}-{destination}-{date}")
    num_options = rng.randint(3, 6)
    results: list[dict] = []

    for i in range(num_options):
        airline_name, airline_code = rng.choice(_AIRLINES)
        stops = rng.choice([0, 0, 1, 1, 2])
        base_price = rng.randint(15000, 85000)
        duration = round(rng.uniform(3.0, 18.0), 1)

        try:
            dep = datetime.fromisoformat(date).replace(
                hour=rng.randint(5, 22), minute=rng.choice([0, 15, 30, 45])
            )
        except ValueError:
            dep = datetime.now().replace(
                hour=rng.randint(5, 22), minute=rng.choice([0, 15, 30, 45])
            )

        arr = dep + timedelta(hours=duration)

        flight = FlightOption(
            airline=airline_name,
            flight_number=f"{airline_code}{rng.randint(100, 999)}",
            origin=origin,
            destination=destination,
            departure_time=dep.isoformat(),
            arrival_time=arr.isoformat(),
            duration_hours=duration,
            price=base_price * passengers,
            currency="INR",
            stops=stops,
            cabin_class="economy",
        )
        results.append(flight.model_dump())

    return results


def search_hotels(
    destination: str,
    checkin: str,
    checkout: str,
    guests: int = 1,
) -> list[dict]:
    """Return mock hotel options.

    Parameters
    ----------
    destination : str
        Destination city.
    checkin : str
        Check-in date ISO string.
    checkout : str
        Check-out date ISO string.
    guests : int
        Number of guests.

    Returns
    -------
    list[dict]
        Serialised HotelOption dicts.
    """
    logger.info(
        "search_hotels  dest=%s  checkin=%s  checkout=%s  guests=%s",
        destination, checkin, checkout, guests,
    )
    rng = random.Random(f"{destination}-{checkin}")
    num_options = rng.randint(4, 8)
    results: list[dict] = []

    for _ in range(num_options):
        name = rng.choice(_HOTEL_NAMES)
        rating = round(rng.uniform(2.5, 5.0), 1)
        price = rng.randint(2000, 25000)
        amenities = rng.sample(_AMENITIES_POOL, k=rng.randint(3, 7))

        hotel = HotelOption(
            name=f"{name} {destination}",
            location=f"{destination} City Centre",
            rating=rating,
            price_per_night=price,
            currency="INR",
            amenities=amenities,
            review_score=round(rng.uniform(6.0, 9.8), 1),
            available=True,
        )
        results.append(hotel.model_dump())

    return results
