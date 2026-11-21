from __future__ import annotations

from typing import Literal

PositionOutcome = Literal["finished", "dnf", "dns", "unknown"]


def normalize_position_cell(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def classify_position(value) -> PositionOutcome:
    text = normalize_position_cell(value)
    if not text:
        return "unknown"
    upper = text.upper()
    if upper in {"DNS"} or "DID NOT START" in upper:
        return "dns"
    if upper in {"DNF"} or "DID NOT FINISH" in upper:
        return "dnf"
    if text.isdigit():
        return "finished"
    return "unknown"