"""Payment tool stub.

Mock implementation for processing payments, validated against the
PaymentReceipt Pydantic schema. Supports simulated failures via
SIMULATE_PAYMENT_FAILURE flag for testing meta-reasoning.
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from typing import Any

from app.settings import SIMULATE_PAYMENT_FAILURE
from schemas.approval_schema import PaymentReceipt

logger = logging.getLogger(__name__)


def process_payment(
    amount: float = 0.0,
    currency: str = "INR",
    method: str = "credit_card",
    **kwargs: Any,
) -> dict[str, Any]:
    """Process a payment (stub).

    Parameters
    ----------
    amount : float
        The payment amount.
    currency : str
        The currency code (e.g. INR, USD).
    method : str
        Payment method (credit_card, debit_card, upi, etc.).

    Returns
    -------
    dict
        A PaymentReceipt serialised as a dict.

    Raises
    ------
    RuntimeError
        If SIMULATE_PAYMENT_FAILURE is True and the random check fails (30% rate).
        This is intentional — it exercises the meta-reasoning recovery path.
    """
    logger.warning("process_payment: STUB — no real payment is being processed.")

    if SIMULATE_PAYMENT_FAILURE and random.random() < 0.3:
        raise RuntimeError(
            f"Payment processing failed: Gateway timeout for {amount} {currency} "
            f"via {method}. (Simulated failure)"
        )

    seed = f"{amount}-{currency}-{method}-{time.time()}"
    transaction_id = "TXN-" + hashlib.md5(seed.encode()).hexdigest()[:8].upper()

    receipt = PaymentReceipt(
        transaction_id=transaction_id,
        type="payment",
        status="completed",
        amount=amount,
        currency=currency,
        method=method,
        details=kwargs,
        processed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        is_stub=True,
    )
    return receipt.model_dump()


