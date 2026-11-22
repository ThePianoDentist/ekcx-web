"""Load repo-root `.env` into os.environ (no-op if missing)."""

from __future__ import annotations

from pathlib import Path

_LOADED = False
_ROOT = Path(__file__).resolve().parents[1]


def load_local_env() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    env_file = _ROOT / ".env"
    if not env_file.is_file():
        return
    from dotenv import load_dotenv

    load_dotenv(env_file, override=False)