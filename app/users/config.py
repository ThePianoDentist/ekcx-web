from __future__ import annotations

import os


def get_session_secret() -> str:
    secret = os.environ.get("EKCX_SESSION_SECRET", "").strip()
    if not secret:
        raise RuntimeError(
            "EKCX_SESSION_SECRET is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret