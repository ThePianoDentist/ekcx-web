from __future__ import annotations

import re
from email.utils import parseaddr

from app.mail.domain.errors import EmailDeliveryError

_ADDR_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# Resend (and most providers) refuse reserved / placeholder domains.
BLOCKED_RECIPIENT_DOMAINS = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "test",
        "invalid",
        "localhost",
    }
)


def normalize_recipient(raw: str) -> str:
    """Return bare email; accepts `you@host` or `Name <you@host>`."""
    trimmed = raw.strip()
    _name, addr = parseaddr(trimmed)
    if addr:
        return addr.strip().lower()
    return trimmed.lower()


def validate_recipient(address: str, *, for_resend: bool = False) -> str:
    """Return normalized address or raise EmailDeliveryError."""
    normalized = normalize_recipient(address)
    if not normalized or not _ADDR_RE.match(normalized):
        raise EmailDeliveryError(
            f"Invalid recipient {address!r}. Use user@domain.tld or Name <user@domain.tld>."
        )
    domain = normalized.rsplit("@", 1)[-1]
    if for_resend and domain in BLOCKED_RECIPIENT_DOMAINS:
        raise EmailDeliveryError(
            f"Resend will not deliver to @{domain} (reserved/placeholder domain). "
            "Use your real inbox, or a Resend test address such as delivered@resend.dev — "
            "see https://resend.com/docs/knowledge-base/what-email-addresses-to-use-for-testing"
        )
    return normalized