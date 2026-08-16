"""Notifications tool module — Send email and SMS confirmations."""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def send_email_confirmation(
    recipient: str,
    subject: str = "Booking Confirmation",
    booking_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Send an email confirmation for a booking or payment."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    booking_ref = booking_id or kwargs.get("booking_ref", "N/A")
    
    logger.info("send_email_confirmation: to=%s subject='%s' booking_id=%s", recipient, subject, booking_ref)
    
    return {
        "status": "sent",
        "recipient": recipient,
        "subject": subject,
        "booking_id": booking_ref,
        "details": details or kwargs.get("details", {}),
        "timestamp": timestamp,
        "success": True,
    }


def send_sms_confirmation(
    recipient: str,
    booking_id: Optional[str] = None,
    message_status: str = "sent",
    details: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Send an SMS confirmation for a booking or payment."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    booking_ref = booking_id or kwargs.get("booking_ref", "N/A")
    
    logger.info("send_sms_confirmation: to=%s booking_id=%s status=%s", recipient, booking_ref, message_status)
    
    return {
        "status": "sent",
        "recipient": recipient,
        "booking_id": booking_ref,
        "message_status": message_status,
        "details": details or kwargs.get("details", {}),
        "timestamp": timestamp,
        "success": True,
    }
