"""Review-step helpers: CSV edits, diffs, confirmation validation."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from io import StringIO
from typing import Dict, List, Tuple

import pandas as pd

from app.participants.domain.name_normalisation import NameSuggestion
from scripts.generate_standings_2025 import (
    normalize_first_name,
    normalize_name,
    resolve_canonical_name,
)

RiderKey = Tuple[str, str]


class ConfirmValidationError(Exception):
    def __init__(self, message: str, unacknowledged: List[NameSuggestion] | None = None) -> None:
        self.message = message
        self.unacknowledged = unacknowledged or []
        super().__init__(message)


def csv_text_diff(old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile="previous",
            tofile="uploaded",
        )
    )


def apply_maps_to_csv(
    csv_text: str,
    rider_map: Dict[RiderKey, RiderKey],
    team_map: Dict[str, str],
) -> str:
    df = pd.read_csv(StringIO(csv_text))
    if "Last Name" not in df.columns:
        return csv_text
    changed = False
    for idx, row in df.iterrows():
        last = normalize_name(str(row.get("Last Name", "")))
        first = normalize_first_name(str(row.get("First Name", "")))
        if not last and not first:
            continue
        rider_key = (last, first)
        norm_key = (rider_key[0].upper(), rider_key[1].upper())
        if norm_key in {(k[0].upper(), k[1].upper()) for k in rider_map}:
            for raw, canon in rider_map.items():
                if raw[0].upper() == last.upper() and raw[1].upper() == first.upper():
                    rider_key = raw
                    break
        if rider_key in rider_map:
            canon = resolve_canonical_name(rider_key, rider_map)
            if df.at[idx, "Last Name"] != canon[0] or df.at[idx, "First Name"] != canon[1]:
                df.at[idx, "Last Name"] = canon[0]
                df.at[idx, "First Name"] = canon[1]
                changed = True
        if "Team" in df.columns and pd.notna(row.get("Team")):
            team = str(row["Team"]).strip()
            if team:
                new_team = resolve_canonical_name(team, team_map)
                if new_team != team:
                    df.at[idx, "Team"] = new_team
                    changed = True
    if not changed:
        return csv_text
    buf = StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


@dataclass
class ExportNameRows:
    """Parsed names from one export for validation."""

    riders: List[RiderKey]
    teams: List[str]


def names_in_csv(csv_text: str) -> ExportNameRows:
    df = pd.read_csv(StringIO(csv_text))
    riders: List[RiderKey] = []
    teams: List[str] = []
    for _, row in df.iterrows():
        last = normalize_name(str(row.get("Last Name", "")))
        first = normalize_first_name(str(row.get("First Name", "")))
        if last or first:
            riders.append((last, first))
        if "Team" in df.columns and pd.notna(row.get("Team")):
            team = str(row["Team"]).strip()
            if team:
                teams.append(team)
    return ExportNameRows(riders=riders, teams=teams)


def _csv_reflects_suggestion(csv_text: str, suggestion: NameSuggestion) -> bool:
    names = names_in_csv(csv_text)
    if suggestion.kind == "rider":
        parts_t = [p.strip() for p in suggestion.target.split(",", 1)]
        if len(parts_t) != 2:
            return False
        target = (normalize_name(parts_t[0]), normalize_first_name(parts_t[1]))
        parts_s = [p.strip() for p in suggestion.source.split(",", 1)]
        source = (
            (normalize_name(parts_s[0]), normalize_first_name(parts_s[1]))
            if len(parts_s) == 2
            else None
        )
        has_target = target in names.riders or any(
            r[0].upper() == target[0].upper() and r[1].upper() == target[1].upper()
            for r in names.riders
        )
        if source:
            still_source = source in names.riders or any(
                r[0].upper() == source[0].upper() and r[1].upper() == source[1].upper()
                for r in names.riders
            )
            return has_target and not still_source
        return has_target
    return suggestion.target in names.teams and suggestion.source not in names.teams


def validate_confirm(
    csv_text: str,
    new_suggestions: List[NameSuggestion],
    accepted_ids: set[str],
    ignored_ids: set[str],
) -> None:
    """Reject when pending suggestions are neither applied in CSV nor explicitly ignored."""
    pending = [s for s in new_suggestions if s.reason != "stored"]
    unacked: List[NameSuggestion] = []
    for suggestion in pending:
        if suggestion.id in ignored_ids:
            continue
        if suggestion.id in accepted_ids:
            continue
        if _csv_reflects_suggestion(csv_text, suggestion):
            continue
        unacked.append(suggestion)
    if unacked:
        raise ConfirmValidationError(
            "Some suggested name changes were not applied or marked as intentionally ignored.",
            unacked,
        )