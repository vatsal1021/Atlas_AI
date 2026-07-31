"""Weather tool — mock implementation for Phase 1.

Returns realistic fake weather data for any destination and date range.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

from schemas.tool_schema import DailyWeather

logger = logging.getLogger(__name__)

_CONDITIONS = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Heavy Rain", "Thunderstorm", "Clear", "Overcast"]


def get_weather(
    destination: str,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Return mock daily weather forecasts.

    Parameters
    ----------
    destination : str
        Destination city.
    start_date : str
        ISO date string for the start.
    end_date : str
        ISO date string for the end.

    Returns
    -------
    list[dict]
        Serialised DailyWeather dicts.
    """
    logger.info(
        "get_weather  dest=%s  start=%s  end=%s",
        destination, start_date, end_date,
    )
    rng = random.Random(f"{destination}-{start_date}")

    try:
        start = datetime.fromisoformat(start_date).date()
        end = datetime.fromisoformat(end_date).date()
    except ValueError:
        start = datetime.now().date()
        end = start + timedelta(days=5)

    days = max((end - start).days + 1, 1)
    results: list[dict] = []

    for i in range(days):
        day_date = start + timedelta(days=i)
        temp_high = round(rng.uniform(18.0, 38.0), 1)
        temp_low = round(temp_high - rng.uniform(4.0, 12.0), 1)
        condition = rng.choice(_CONDITIONS)

        # Rain probability correlates with condition
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
