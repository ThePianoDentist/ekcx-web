"""Write parsed season results and computed standings into SQLite."""

from __future__ import annotations

from datetime import date
from typing import Dict

from sqlalchemy.orm import Session

from app.events.data.models import Event
from app.participants.data.models import Club, ClubMembership, Participant
from app.participants.domain.name_normalisation import RiderKey, build_stored_maps, load_rules
from app.results.data.models import Result
from app.standings.data.models import ClubCategoryPoints, ClubStanding, EventPoints, Standing
from scripts.generate_standings_2025 import (
    calculate_standings,
    calculate_team_standings,
    normalize_rider_and_team_names,
)


def stamp_raw_names(all_results: dict) -> None:
    for rounds in all_results.values():
        for rows in rounds.values():
            for result in rows:
                result["raw_last_name"] = result["last_name"]
                result["raw_first_name"] = result["first_name"]
                result["raw_team"] = result["team"]


def _club(session: Session, clubs: dict, name: str) -> Club | None:
    if not name:
        return None
    club = clubs.get(name)
    if club is None:
        club = Club(name=name)
        session.add(club)
        session.flush()
        clubs[name] = club
    return club


def _participant(
    session: Session,
    people: dict,
    clubs: dict,
    last_name: str,
    first_name: str,
    team: str,
    season_start: date,
) -> Participant:
    key = (last_name, first_name)
    person = people.get(key)
    if person is None:
        club = _club(session, clubs, team)
        person = Participant(
            last_name=last_name,
            first_name=first_name,
            club_id=club.id if club else None,
        )
        session.add(person)
        session.flush()
        if club is not None:
            session.add(
                ClubMembership(
                    participant_id=person.id,
                    club_id=club.id,
                    joined_on=season_start,
                )
            )
        people[key] = person
    elif person.club_id is None and team:
        club = _club(session, clubs, team)
        person.club_id = club.id if club else None
        if club is not None:
            session.add(
                ClubMembership(
                    participant_id=person.id,
                    club_id=club.id,
                    joined_on=season_start,
                )
            )
    return person


def persist_season_results(
    session: Session,
    year: int,
    all_results: Dict[str, Dict[str, list]],
    events_by_round: Dict[int, Event],
    season_start: date,
    *,
    merge_similar: bool = False,
    stored_rider_rules: dict[RiderKey, RiderKey] | None = None,
    stored_team_rules: dict[str, str] | None = None,
) -> tuple[int, int]:
    """Insert Result, Standing, and related rows. Caller clears stale rows first."""
    stamp_raw_names(all_results)
    if stored_rider_rules is None:
        rules = load_rules(session)
        stored_rider, stored_team = build_stored_maps(rules)
    else:
        stored_rider = stored_rider_rules
        stored_team = stored_team_rules or {}
    normalize_rider_and_team_names(
        all_results,
        merge_similar=merge_similar,
        apply_to_results=True,
        stored_rider_rules=stored_rider,
        stored_team_rules=stored_team,
        use_script_predefined=False,
        log=False,
    )
    category_standings = calculate_standings(all_results)
    team_standings = calculate_team_standings(all_results, category_standings)

    clubs: dict = {}
    people: dict = {}

    for category, rounds in all_results.items():
        for round_num, rows in rounds.items():
            event = events_by_round[int(round_num)]
            for result in rows:
                person = _participant(
                    session,
                    people,
                    clubs,
                    result["last_name"],
                    result["first_name"],
                    result["team"],
                    season_start,
                )
                club = _club(session, clubs, result["team"])
                session.add(
                    Result(
                        event_id=event.id,
                        category=category,
                        participant_id=person.id,
                        club_id=club.id if club else None,
                        raw_last_name=result["raw_last_name"],
                        raw_first_name=result["raw_first_name"],
                        raw_club=result["raw_team"] or None,
                        position=result["position"],
                        dnf=bool(result["dnf"]),
                        points=result["points"],
                        category_detail=result["category"] or None,
                        gender=result["gender"] or None,
                    )
                )

    for category, riders in category_standings.items():
        for rider in riders:
            person = people[(rider["last_name"], rider["first_name"])]
            club = _club(session, clubs, rider["team"])
            standing = Standing(
                year=year,
                category=category,
                participant_id=person.id,
                club_id=club.id if club else None,
                total_points=rider["total_points"],
                points_excl_lowest=rider["points_excl_lowest"],
            )
            session.add(standing)
            session.flush()
            for round_num, points in rider["points_by_round"].items():
                session.add(
                    EventPoints(
                        standing_id=standing.id,
                        event_id=events_by_round[int(round_num)].id,
                        points=points,
                    )
                )

    for team in team_standings:
        club = clubs[team["team"]]
        club_standing = ClubStanding(year=year, club_id=club.id, total_points=team["total"])
        session.add(club_standing)
        session.flush()
        for category in ("womens", "mens", "u12", "youth", "v40", "v50"):
            points = team[category]
            if not points:
                continue
            session.add(
                ClubCategoryPoints(
                    club_standing_id=club_standing.id,
                    category=category,
                    points=points,
                )
            )

    standings_rows = sum(len(v) for v in category_standings.values())
    return len(people), standings_rows