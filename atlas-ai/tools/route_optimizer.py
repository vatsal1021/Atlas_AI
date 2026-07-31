"""Route Optimizer tool stub.

Given a list of locations/activities for a day, optimises the visiting order
using a nearest-neighbour heuristic on lat/lng distances.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points (km)."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def optimize_route(
    locations: list[dict] | None = None,
    **kwargs: Any,
) -> list[dict]:
    """Optimise visiting order using nearest-neighbour heuristic.

    Parameters
    ----------
    locations : list[dict]
        Each dict should have at least: ``name``, ``lat``, ``lng``.
        Example: [{"name": "Senso-ji", "lat": 35.7148, "lng": 139.7967}, ...]

    Returns
    -------
    list[dict]
        The same locations reordered for minimal travel distance,
        with ``order`` and ``distance_from_prev_km`` fields added.
    """
    if not locations:
        return []

    logger.info("optimize_route: Optimising %d locations.", len(locations))

    # Nearest-neighbour starting from the first location
    remaining = list(range(len(locations)))
    current = remaining.pop(0)
    order = [current]

    while remaining:
        cur_loc = locations[current]
        best_idx = None
        best_dist = float("inf")

        for idx in remaining:
            next_loc = locations[idx]
            dist = _haversine(
                cur_loc.get("lat", 0), cur_loc.get("lng", 0),
                next_loc.get("lat", 0), next_loc.get("lng", 0),
            )
            if dist < best_dist:
                best_dist = dist
                best_idx = idx

        remaining.remove(best_idx)
        order.append(best_idx)
        current = best_idx

    # Build optimised list with distances
    result = []
    for i, idx in enumerate(order):
        loc = dict(locations[idx])
        loc["order"] = i + 1
        if i == 0:
            loc["distance_from_prev_km"] = 0.0
        else:
            prev = locations[order[i - 1]]
            loc["distance_from_prev_km"] = round(
                _haversine(
                    prev.get("lat", 0), prev.get("lng", 0),
                    loc.get("lat", 0), loc.get("lng", 0),
                ),
                2,
            )
        result.append(loc)

    total_distance = sum(r["distance_from_prev_km"] for r in result)
    logger.info("optimize_route: Total distance = %.2f km", total_distance)

    return result
