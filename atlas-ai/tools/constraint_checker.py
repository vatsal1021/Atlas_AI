"""Constraint checker tool.

Deterministic validation of a plan against budget, date, and preference constraints.
"""

from __future__ import annotations

import logging

from schemas.tool_schema import ConstraintViolation

logger = logging.getLogger(__name__)


def check_constraints(
    plan: dict,
    constraints: list[str] | None = None,
    budget: float | None = None,
    currency: str = "INR",
) -> list[dict]:
    """Check a plan for constraint violations.

    Parameters
    ----------
    plan : dict
        The plan or evidence dict to validate. Expected keys:
        ``total_cost``, ``days``, ``preferences_met``.
    constraints : list[str] | None
        Explicit constraints from the user.
    budget : float | None
        Budget cap.
    currency : str
        Budget currency code.

    Returns
    -------
    list[dict]
        Serialised ConstraintViolation dicts. Empty list = no violations.
    """
    logger.info("check_constraints  budget=%s %s  constraints=%s", budget, currency, constraints)
    violations: list[ConstraintViolation] = []

    # --- Budget check ---
    total_cost = plan.get("total_cost", 0)
    if budget is not None and total_cost > budget:
        violations.append(
            ConstraintViolation(
                constraint=f"Budget <= {budget} {currency}",
                violation=f"Estimated cost {total_cost} {currency} exceeds budget by {total_cost - budget} {currency}",
                severity="error",
                suggestion="Consider cheaper flights, lower-rated hotels, or reducing trip duration.",
            )
        )

    # --- Date sanity ---
    start = plan.get("start_date", "")
    end = plan.get("end_date", "")
    if start and end and start > end:
        violations.append(
            ConstraintViolation(
                constraint="start_date <= end_date",
                violation=f"Start date {start} is after end date {end}",
                severity="error",
                suggestion="Swap the dates.",
            )
        )

    # --- Custom constraint keywords ---
    if constraints:
        for c in constraints:
            lower_c = c.lower()
            # Simple keyword matching against plan details
            if "vegetarian" in lower_c and not plan.get("vegetarian_options", True):
                violations.append(
                    ConstraintViolation(
                        constraint=c,
                        violation="No vegetarian dining options confirmed",
                        severity="warning",
                        suggestion="Search specifically for vegetarian-friendly restaurants.",
                    )
                )

    return [v.model_dump() for v in violations]
