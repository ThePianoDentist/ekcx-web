from __future__ import annotations

import os
from typing import Literal

EmailMode = Literal["log", "resend", "disabled"]


def get_email_mode() -> EmailMode:
    raw = os.environ.get("EKCX_EMAIL_MODE", "log").strip().lower()
    if raw in ("log", "resend", "disabled"):
        return raw  # type: ignore[return-value]
    raise RuntimeError(
        f"Invalid EKCX_EMAIL_MODE={raw!r}. Use log, resend, or disabled."
    )


def get_resend_api_key() -> str:
    return os.environ.get("RESEND_API_KEY", "").strip()


def get_default_from() -> str:
    return os.environ.get("EKCX_EMAIL_FROM", "").strip()