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
    origin: str = "Delhi",
    destination: str = "",
    date: str = "",
    passengers: int = 1,
    **kwargs,
) -> list[dict]:
    """Return mock flight options."""
    destination = destination or kwargs.get("location") or kwargs.get("to") or "Jaipur"
    origin = origin or kwargs.get("from") or "Delhi"
    date = date or kwargs.get("departure_date") or kwargs.get("start_date") or datetime.now().strftime("%Y-%m-%d")
    passengers = passengers or kwargs.get("guests") or kwargs.get("travelers") or 1

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
        base_price = rng.randint(3000, 15000)
        duration = round(rng.uniform(1.5, 6.0), 1)

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
    destination: str = "",
    checkin: str = "",
    checkout: str = "",
    guests: int = 1,
    **kwargs,
) -> list[dict]:
    """Return mock hotel options."""
    destination = destination or kwargs.get("location") or kwargs.get("city") or "Jaipur"
    checkin = checkin or kwargs.get("start_date") or kwargs.get("check_in") or datetime.now().strftime("%Y-%m-%d")
    checkout = checkout or kwargs.get("end_date") or kwargs.get("check_out") or (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    guests = guests or kwargs.get("travelers") or kwargs.get("people") or 1

    logger.info(
        "search_hotels  dest=%s  checkin=%s  checkout=%s  guests=%s",
        destination, checkin, checkout, guests,
    )
    rng = random.Random(f"{destination}-{checkin}")
    num_options = rng.randint(4, 8)
    results: list[dict] = []

    for _ in range(num_options):
        name = rng.choice(_HOTEL_NAMES)
        rating = round(rng.uniform(3.5, 5.0), 1)
        price = rng.randint(2000, 8000)
        amenities = rng.sample(_AMENITIES_POOL, k=rng.randint(3, 7))

        hotel = HotelOption(
            name=f"{name} {destination}",
            location=f"{destination} City Centre",
            rating=rating,
            price_per_night=price,
            currency="INR",
            amenities=amenities,
            review_score=round(rng.uniform(7.0, 9.8), 1),
            available=True,
        )
        results.append(hotel.model_dump())

    return results


_TRAIN_NAMES = [
    ("Vande Bharat Express", "22435"),
    ("Shatabdi Express", "12004"),
    ("Rajdhani Express", "12423"),
    ("Tejas Express", "82501"),
    ("Garib Rath Express", "12204"),
    ("Intercity Express", "14210"),
]


def search_trains(
    origin: str = "Kanpur",
    destination: str = "Delhi",
    date: str = "",
    passengers: int = 1,
    **kwargs,
) -> list[dict]:
    """Return mock train options."""
    destination = destination or kwargs.get("location") or kwargs.get("to") or "Delhi"
    origin = origin or kwargs.get("from") or "Kanpur"
    date = date or kwargs.get("departure_date") or kwargs.get("start_date") or datetime.now().strftime("%Y-%m-%d")
    passengers = passengers or kwargs.get("guests") or kwargs.get("travelers") or 1

    logger.info(
        "search_trains  origin=%s  dest=%s  date=%s  pax=%s",
        origin, destination, date, passengers,
    )
    rng = random.Random(f"{origin}-{destination}-{date}-train")
    num_options = rng.randint(3, 5)
    results: list[dict] = []

    for i in range(num_options):
        train_name, train_number = rng.choice(_TRAIN_NAMES)
        travel_class = rng.choice(["CC", "EC", "3A", "2A", "1A"])
        price = rng.randint(450, 2400) * passengers
        duration = round(rng.uniform(4.0, 8.5), 1)

        try:
            dep = datetime.fromisoformat(date).replace(
                hour=rng.randint(6, 21), minute=rng.choice([0, 15, 30, 45])
            )
        except ValueError:
            dep = datetime.now().replace(
                hour=rng.randint(6, 21), minute=rng.choice([0, 15, 30, 45])
            )

        arr = dep + timedelta(hours=duration)

        train_info = {
            "train_name": train_name,
            "train_number": train_number,
            "origin": origin,
            "destination": destination,
            "departure_time": dep.isoformat(),
            "arrival_time": arr.isoformat(),
            "duration_hours": duration,
            "travel_class": travel_class,
            "price": price,
            "currency": "INR",
            "seats_available": rng.randint(12, 140),
            "status": "available",
        }
        results.append(train_info)

    return results


# Aliases
flight_search = search_flights
hotel_search = search_hotels
train_search = search_trains

