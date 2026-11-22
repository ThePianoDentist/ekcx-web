from __future__ import annotations

import logging

from app.mail.config import get_default_from, get_email_mode, get_resend_api_key
from app.mail.data import resend_api
from app.mail.domain.addresses import normalize_recipient, validate_recipient
from app.mail.domain.errors import EmailDeliveryError
from app.mail.domain.outbound import OutboundEmail

logger = logging.getLogger(__name__)

__all__ = ["EmailDeliveryError", "send_email"]


def send_email(message: OutboundEmail) -> str | None:
    """Send or simulate an email. Returns Resend message id, or None in log/disabled mode."""
    mode = get_email_mode()
    if mode == "disabled":
        logger.info("email disabled: to=%s subject=%r", message.to, message.subject)
        return None

    from_addr = message.from_address or get_default_from()
    if mode == "resend":
        if not from_addr:
            raise EmailDeliveryError(
                "EKCX_EMAIL_FROM is not set (or pass from_address on the message)."
            )
        api_key = get_resend_api_key()
        if not api_key:
            raise EmailDeliveryError("RESEND_API_KEY is not set.")
        to_addr = validate_recipient(message.to, for_resend=True)
        normalized = OutboundEmail(
            to=to_addr,
            subject=message.subject,
            text=message.text,
            html=message.html,
            from_address=message.from_address,
        )
        return resend_api.send(api_key, from_addr, normalized)

    # log (default local / pytest)
    to_display = normalize_recipient(message.to)
    logger.info(
        "email log mode: from=%r to=%r subject=%r\n---\n%s\n---",
        from_addr or "(unset)",
        to_display,
        message.subject,
        message.text,
    )
    return None