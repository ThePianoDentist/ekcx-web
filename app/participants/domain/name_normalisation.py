"""Load and apply cross-season rider/club name rules; build ingest suggestions."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.participants.data.models import ClubNameRule, RiderNameRule
from scripts.generate_standings_2025 import (
    normalize_first_name,
    normalize_name,
    normalize_rider_and_team_names,
    resolve_canonical_name,
)

RiderKey = Tuple[str, str]


@dataclass
class LoadedRules:
    rider_rows: List[RiderNameRule] = field(default_factory=list)
    club_rows: List[ClubNameRule] = field(default_factory=list)


@dataclass
class NameSuggestion:
    """A proposed merge not yet stored as a rule."""

    id: str
    kind: Literal["rider", "team"]
    reason: Literal["case", "similarity", "stored"]
    source: str
    target: str
    rounds: List[str]
    clubs: List[str] = field(default_factory=list)


def load_rules(session: Session) -> LoadedRules:
    riders = list(session.scalars(select(RiderNameRule)).all())
    clubs = list(session.scalars(select(ClubNameRule)).all())
    return LoadedRules(rider_rows=riders, club_rows=clubs)


def build_stored_maps(rules: LoadedRules) -> Tuple[Dict[RiderKey, RiderKey], Dict[str, str]]:
    rider: Dict[RiderKey, RiderKey] = {}
    for row in rules.rider_rows:
        raw_key = (normalize_name(row.raw_last_name), normalize_first_name(row.raw_first_name))
        canon = (
            normalize_name(row.canonical_last_name),
            normalize_first_name(row.canonical_first_name),
        )
        if raw_key != canon:
            rider[raw_key] = canon
    club: Dict[str, str] = {row.raw_name: row.canonical_name for row in rules.club_rows}
    return rider, club


def _rider_context(
    all_results: Dict[str, Dict[str, List[dict]]],
    rider: RiderKey,
) -> Tuple[List[str], List[str]]:
    rounds: set[str] = set()
    clubs: set[str] = set()
    for rounds_map in all_results.values():
        for round_num, rows in rounds_map.items():
            for row in rows:
                key = (row["last_name"], row["first_name"])
                if key == rider or (
                    key[0].upper() == rider[0].upper() and key[1].upper() == rider[1].upper()
                ):
                    rounds.add(round_num)
                    if row.get("team"):
                        clubs.add(row["team"])
    return sorted(rounds, key=int), sorted(clubs)


def _team_context(all_results: Dict[str, Dict[str, List[dict]]], team: str) -> List[str]:
    rounds: set[str] = set()
    for rounds_map in all_results.values():
        for round_num, rows in rounds_map.items():
            for row in rows:
                if row.get("team") == team:
                    rounds.add(round_num)
    return sorted(rounds, key=int)


def compute_normalisation_maps(
    all_results: Dict[str, Dict[str, List[dict]]],
    *,
    merge_similar: bool,
    stored_rider: Dict[RiderKey, RiderKey],
    stored_team: Dict[str, str],
) -> Tuple[Dict[RiderKey, RiderKey], Dict[str, str]]:
    working = copy.deepcopy(all_results)
    return normalize_rider_and_team_names(
        working,
        merge_similar=merge_similar,
        apply_to_results=False,
        stored_rider_rules=stored_rider,
        stored_team_rules=stored_team,
        use_script_predefined=False,
        log=False,
    )


def stored_applications(
    all_results: Dict[str, Dict[str, List[dict]]],
    rules: LoadedRules,
) -> List[NameSuggestion]:
    stored_rider, stored_team = build_stored_maps(rules)
    maps = compute_normalisation_maps(
        all_results,
        merge_similar=False,
        stored_rider=stored_rider,
        stored_team=stored_team,
    )
    out: List[NameSuggestion] = []
    for rider, target in maps[0].items():
        if rider == target:
            continue
        rounds, clubs = _rider_context(all_results, rider)
        out.append(
            NameSuggestion(
                id=f"stored-rider:{rider[0]}:{rider[1]}",
                kind="rider",
                reason="stored",
                source=f"{rider[0]}, {rider[1]}",
                target=f"{target[0]}, {target[1]}",
                rounds=rounds,
                clubs=clubs,
            )
        )
    for team, target in maps[1].items():
        if team == target:
            continue
        out.append(
            NameSuggestion(
                id=f"stored-team:{team}",
                kind="team",
                reason="stored",
                source=team,
                target=target,
                rounds=_team_context(all_results, team),
            )
        )
    return out


def new_suggestions(
    all_results: Dict[str, Dict[str, List[dict]]],
    rules: LoadedRules,
) -> List[NameSuggestion]:
    stored_rider, stored_team = build_stored_maps(rules)
    without = compute_normalisation_maps(
        all_results,
        merge_similar=False,
        stored_rider=stored_rider,
        stored_team=stored_team,
    )
    with_similar = compute_normalisation_maps(
        all_results,
        merge_similar=True,
        stored_rider=stored_rider,
        stored_team=stored_team,
    )
    out: List[NameSuggestion] = []

    for rider, target in with_similar[0].items():
        if rider in without[0] and without[0][rider] == target:
            continue
        if rider == target:
            continue
        rounds, clubs = _rider_context(all_results, rider)
        reason: Literal["case", "similarity"] = (
            "case" if rider[0].upper() == target[0].upper() and rider[1].upper() == target[1].upper() else "similarity"
        )
        out.append(
            NameSuggestion(
                id=f"new-rider:{rider[0]}:{rider[1]}",
                kind="rider",
                reason=reason,
                source=f"{rider[0]}, {rider[1]}",
                target=f"{target[0]}, {target[1]}",
                rounds=rounds,
                clubs=clubs,
            )
        )

    for team, target in with_similar[1].items():
        if team in without[1] and without[1][team] == target:
            continue
        if team == target:
            continue
        out.append(
            NameSuggestion(
                id=f"new-team:{team}",
                kind="team",
                reason="similarity",
                source=team,
                target=target,
                rounds=_team_context(all_results, team),
            )
        )
    return out


def apply_stored_rules_to_results(
    all_results: Dict[str, Dict[str, List[dict]]],
    rules: LoadedRules,
) -> None:
    stored_rider, stored_team = build_stored_maps(rules)
    normalize_rider_and_team_names(
        all_results,
        merge_similar=False,
        apply_to_results=True,
        stored_rider_rules=stored_rider,
        stored_team_rules=stored_team,
        use_script_predefined=False,
        log=False,
    )


def maps_for_accepted(
    suggestions: List[NameSuggestion],
    accepted_ids: set[str],
    rules: LoadedRules,
) -> Tuple[Dict[RiderKey, RiderKey], Dict[str, str]]:
    stored_rider, stored_team = build_stored_maps(rules)
    rider = dict(stored_rider)
    team = dict(stored_team)
    for item in suggestions:
        if item.id not in accepted_ids:
            continue
        if item.kind == "rider":
            parts_s = [p.strip() for p in item.source.split(",", 1)]
            parts_t = [p.strip() for p in item.target.split(",", 1)]
            if len(parts_s) == 2 and len(parts_t) == 2:
                rider[(parts_s[0], parts_s[1])] = (parts_t[0], parts_t[1])
        else:
            team[item.source] = item.target
    return rider, team


def upsert_accepted_suggestions(
    session: Session,
    suggestions: List[NameSuggestion],
    accepted_ids: set[str],
    source: str,
) -> None:
    for item in suggestions:
        if item.id not in accepted_ids or item.reason == "stored":
            continue
        if item.kind == "rider":
            parts_s = [p.strip() for p in item.source.split(",", 1)]
            parts_t = [p.strip() for p in item.target.split(",", 1)]
            if len(parts_s) != 2 or len(parts_t) != 2:
                continue
            raw = (parts_s[0], parts_s[1])
            canon = (parts_t[0], parts_t[1])
            existing = session.scalar(
                select(RiderNameRule).where(
                    RiderNameRule.raw_last_name == raw[0],
                    RiderNameRule.raw_first_name == raw[1],
                    RiderNameRule.category == "",
                    RiderNameRule.event_id.is_(None),
                )
            )
            if existing:
                existing.canonical_last_name = canon[0]
                existing.canonical_first_name = canon[1]
                existing.source = source
            else:
                session.add(
                    RiderNameRule(
                        raw_last_name=raw[0],
                        raw_first_name=raw[1],
                        canonical_last_name=canon[0],
                        canonical_first_name=canon[1],
                        category="",
                        source=source,
                    )
                )
        else:
            existing = session.scalar(
                select(ClubNameRule).where(ClubNameRule.raw_name == item.source)
            )
            if existing:
                existing.canonical_name = item.target
                existing.source = source
            else:
                session.add(
                    ClubNameRule(
                        raw_name=item.source,
                        canonical_name=item.target,
                        source=source,
                    )
                )


def upsert_rules_from_maps(
    session: Session,
    rider_map: Dict[RiderKey, RiderKey],
    team_map: Dict[str, str],
    source: str,
) -> None:
    for raw, canon in rider_map.items():
        existing = session.scalar(
            select(RiderNameRule).where(
                RiderNameRule.raw_last_name == raw[0],
                RiderNameRule.raw_first_name == raw[1],
                RiderNameRule.category == "",
                RiderNameRule.event_id.is_(None),
            )
        )
        if existing:
            existing.canonical_last_name = canon[0]
            existing.canonical_first_name = canon[1]
            existing.source = source
        else:
            session.add(
                RiderNameRule(
                    raw_last_name=raw[0],
                    raw_first_name=raw[1],
                    canonical_last_name=canon[0],
                    canonical_first_name=canon[1],
                    category="",
                    source=source,
                )
            )

    for raw_name, canonical_name in team_map.items():
        existing = session.scalar(
            select(ClubNameRule).where(ClubNameRule.raw_name == raw_name)
        )
        if existing:
            existing.canonical_name = canonical_name
            existing.source = source
        else:
            session.add(
                ClubNameRule(
                    raw_name=raw_name,
                    canonical_name=canonical_name,
                    source=source,
                )
            )


def suggestion_id_for_pair(kind: str, source: str, target: str) -> str:
    if kind == "rider":
        parts = [p.strip() for p in source.split(",", 1)]
        return f"new-rider:{parts[0]}:{parts[1]}" if len(parts) == 2 else f"new-rider:{source}"
    return f"new-team:{source}"