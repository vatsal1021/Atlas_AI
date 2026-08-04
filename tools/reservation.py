"""Reservation tool stub.

Mock implementation for making activity / restaurant reservations,
validated against the ReservationConfirmation Pydantic schema.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from schemas.approval_schema import ReservationConfirmation

logger = logging.getLogger(__name__)


def make_reservation(
    activity: str = "",
    date: str = "",
    participants: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """Make a reservation (stub).

    Parameters
    ----------
    activity : str
        The activity or restaurant to reserve.
    date : str
        The reservation date (ISO format).
    participants : int
        Number of participants.

    Returns
    -------
    dict
        A ReservationConfirmation serialised as a dict.
    """
    logger.warning("make_reservation: STUB — no real reservation is being made.")

    seed = f"{activity}-{date}-{participants}"
    reservation_id = "RSV-" + hashlib.md5(seed.encode()).hexdigest()[:8].upper()

    confirmation = ReservationConfirmation(
        reservation_id=reservation_id,
        type="reservation",
        status="confirmed",
        activity=activity,
        date=date,
        participants=participants,
        details=kwargs,
        cancellation_policy="Free cancellation up to 24 hours before.",
        reserved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        is_stub=True,
    )
    return confirmation.model_dump()
