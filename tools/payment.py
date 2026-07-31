"""Payment tool stub.

Mock implementation for processing payments.
Supports simulated failures via SIMULATE_PAYMENT_FAILURE flag.
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from typing import Any

from app.settings import SIMULATE_PAYMENT_FAILURE

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
        The currency code.
    method : str
        Payment method (credit_card, debit_card, upi, etc.)

    Returns
    -------
    dict
        A mock PaymentReceipt.

    Raises
    ------
    RuntimeError
        If SIMULATE_PAYMENT_FAILURE is True and the random check fails (30% rate).
    """
    logger.warning("process_payment: STUB — no real payment is being processed.")

    # Simulate payment failure for meta-reasoning testing
    if SIMULATE_PAYMENT_FAILURE and random.random() < 0.3:
        raise RuntimeError(
            f"Payment processing failed: Gateway timeout for {amount} {currency} "
            f"via {method}. (Simulated failure)"
        )

    seed = f"{amount}-{currency}-{method}-{time.time()}"
    transaction_id = "TXN-" + hashlib.md5(seed.encode()).hexdigest()[:8].upper()

    return {
        "transaction_id": transaction_id,
        "type": "payment",
        "status": "completed",
        "amount": amount,
        "currency": currency,
        "method": method,
        "details": kwargs,
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "is_stub": True,
    }
