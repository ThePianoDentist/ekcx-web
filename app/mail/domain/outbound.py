from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutboundEmail:
    to: str
    subject: str
    text: str
    html: str | None = None
    from_address: str | None = None