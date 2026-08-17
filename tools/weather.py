"""Weather tool — resilient implementation.

Returns realistic fake weather data for any destination and date range.
Fully handles parameter alias variations (location, city, place, date, start, end).
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

from schemas.tool_schema import DailyWeather

logger = logging.getLogger(__name__)

_CONDITIONS = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Heavy Rain", "Thunderstorm", "Clear", "Overcast"]


def get_weather(
    destination: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    **kwargs: Any,
) -> list[dict]:
    """Return mock daily weather forecasts with resilient parameter fallbacks.

    Parameters
    ----------
    destination : str | None
        Destination city. Also accepts location, city, place, dest in kwargs.
    start_date : str | None
        ISO date string for start. Also accepts date, start, checkin in kwargs.
    end_date : str | None
        ISO date string for end. Also accepts date, end, checkout in kwargs.

    Returns
    -------
    list[dict]
        Serialised DailyWeather dicts.
    """
    dest = (
        destination
        or kwargs.get("location")
        or kwargs.get("city")
        or kwargs.get("place")
        or kwargs.get("dest")
        or kwargs.get("loc")
        or "Destination"
    )

    s_date_raw = (
        start_date
        or kwargs.get("date")
        or kwargs.get("start")
        or kwargs.get("checkin")
        or kwargs.get("departure_date")
        or ""
    )

    e_date_raw = (
        end_date
        or kwargs.get("end")
        or kwargs.get("checkout")
        or kwargs.get("return_date")
        or (kwargs.get("date") if start_date or kwargs.get("start") else "")
        or ""
    )

    # Parse or default start date
    try:
        if s_date_raw:
            start = datetime.fromisoformat(str(s_date_raw).split("T")[0]).date()
        else:
            start = datetime.now().date()
    except Exception:
        start = datetime.now().date()

    # Parse or default end date
    try:
        if e_date_raw and e_date_raw != s_date_raw:
            end = datetime.fromisoformat(str(e_date_raw).split("T")[0]).date()
        else:
            end = start + timedelta(days=4)
    except Exception:
        end = start + timedelta(days=4)

    if end < start:
        end = start + timedelta(days=4)

    logger.info(
        "get_weather  dest=%s  start=%s  end=%s",
        dest, start, end,
    )
    rng = random.Random(f"{dest}-{start}")

    days = max((end - start).days + 1, 1)
    results: list[dict] = []

    for i in range(days):
        day_date = start + timedelta(days=i)
        temp_high = round(rng.uniform(18.0, 38.0), 1)
        temp_low = round(temp_high - rng.uniform(4.0, 12.0), 1)
        condition = rng.choice(_CONDITIONS)

        rain_map = {
            "Sunny": 0.05, "Clear": 0.05, "Partly Cloudy": 0.15,
            "Cloudy": 0.3, "Overcast": 0.4, "Light Rain": 0.7,
            "Heavy Rain": 0.9, "Thunderstorm": 0.95,
        }
        rain_prob = rain_map.get(condition, 0.2)

        weather = DailyWeather(
            date=day_date.isoformat(),
            temperature_high=temp_high,
            temperature_low=temp_low,
            condition=condition,
            rain_probability=rain_prob,
            humidity=round(rng.uniform(30.0, 95.0), 1),
            wind_speed_kmh=round(rng.uniform(5.0, 40.0), 1),
        )
        results.append(weather.model_dump())

    return results
