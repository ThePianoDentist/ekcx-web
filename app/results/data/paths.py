from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def get_results_root() -> Path:
    override = os.environ.get("EKCX_RESULTS_ROOT")
    if override:
        return Path(override)
    return _REPO_ROOT / "results"