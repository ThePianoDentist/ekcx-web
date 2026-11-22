#!/usr/bin/env python3
"""Load the current season into SQLite and check it against the standings HTML.

2026 rounds 1 and 2 only. Round 3 stays on disk so it can be ingested later.
Older seasons stay on the static HTML pages. Re-running replaces this season.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import build_sqlite_url, create_session_factory
from app.events.data.models import Event
from app.participants.data.models import Club, ClubMembership, NameNormalisation, Participant
from app.results.data.models import Result, ResultExport
from app.results.domain.raw_export import file_to_sanitized_csv, round_export_paths
from app.standings.data.models import ClubCategoryPoints, ClubStanding, EventPoints, Standing
from app.standings.domain.html_standings import parse_rider_standings, parse_team_standings
from scripts.generate_standings_2025 import (
    calculate_standings,
    calculate_team_standings,
    collect_results,
    normalize_rider_and_team_names,
)

YEAR = 2026
# Farthingloe is held back for the first database ingest test.
INCLUDE_ROUNDS = {1, 2}
SEASON_START = date(2026, 9, 13)

# Same metadata the public event pages use. Results are loaded only for INCLUDE_ROUNDS.
EVENTS = [
    {
        "round_number": 1,
        "name": "Round 1: Sandwich",
        "event_date": "September 13, 2026",
        "location": "Sandwich",
        "british_cycling_url": "https://www.britishcycling.org.uk/events/details/338429/East-Kent-Cyclo-Cross-League-Round-1-SandwichTechCross---Tim-Mountford-Memorial-",
        "status": "completed",
    },
    {
        "round_number": 2,
        "name": "Round 2: Dover",
        "event_date": "October 18, 2026",
        "location": "Dover",
        "british_cycling_url": "https://www.britishcycling.org.uk/events/details/340011/East-Kent-Cyclo-Cross-League-Round-2-DukeofYorksCross",
        "status": "completed",
    },
    {
        "round_number": 3,
        "name": "Round 3: Farthingloe",
        "event_date": "November 15, 2026",
        "location": "Farthingloe",
        "british_cycling_url": "https://www.britishcycling.org.uk/events/details/341793/East-Kent-Cyclo-Cross-League-Round-3-FarthingloeCross",
        "status": "upcoming",
    },
    {
        "round_number": 4,
        "name": "Round 4: Lydden",
        "event_date": "December 13, 2026",
        "location": "Lydden",
        "british_cycling_url": "https://www.britishcycling.org.uk/events/details/341794/East-Kent-Cyclo-Cross-League-Round-4-LyddenHillCross",
        "status": "upcoming",
    },
    {
        "round_number": 5,
        "name": "Round 5: Betteshanger",
        "event_date": "January 17, 2027",
        "location": "Betteshanger",
        "british_cycling_url": "https://www.britishcycling.org.uk/events/details/341795/East-Kent-Cyclo-Cross-League-Round-5-BetteshangerCross",
        "status": "upcoming",
    },
]

RIDER_FILES = {
    "womens": "womens.html",
    "v40": "v40.html",
    "v50": "v50.html",
    "youth": "youth.html",
    "u12": "u12.html",
}

# 2026 team table folds seniors into the V40 column.
TEAM_COLUMNS = {
    "Women": "womens",
    "V40": ("mens", "v40"),
    "Under 12": "u12",
    "Under 16": "youth",
    "V50": "v50",
    "Points": "total",
}


def upgrade_schema(root: Path, db_path: Path) -> None:
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")


def clear_league(session: Session) -> None:
    """Drop league rows so a second run replaces this season. Users stay."""
    for model in (
        EventPoints,
        ClubCategoryPoints,
        Result,
        ResultExport,
        NameNormalisation,
        ClubMembership,
        Standing,
        ClubStanding,
        Event,
        Participant,
        Club,
    ):
        session.execute(delete(model))


def _stamp_raw_names(all_results: dict) -> None:
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
                    joined_on=SEASON_START,
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
                    joined_on=SEASON_START,
                )
            )
    return person


def load_raw_exports(
    session: Session,
    events: dict[int, Event],
    results_dir: Path,
) -> int:
    stored = 0
    for round_num in sorted(INCLUDE_ROUNDS):
        event = events[round_num]
        for path in round_export_paths(results_dir, round_num):
            csv_text = file_to_sanitized_csv(path)
            if not csv_text:
                print(f"Skipping empty export: {path.name}", file=sys.stderr)
                continue
            session.add(
                ResultExport(
                    event_id=event.id,
                    filename=path.name,
                    csv_text=csv_text,
                )
            )
            stored += 1
    return stored


def load_season(session: Session, results_dir: Path) -> None:
    all_results = collect_results(results_dir, include_rounds=INCLUDE_ROUNDS)
    _stamp_raw_names(all_results)
    rider_normalizations, _team_normalizations = normalize_rider_and_team_names(all_results)
    category_standings = calculate_standings(all_results)
    team_standings = calculate_team_standings(all_results, category_standings)

    clear_league(session)
    events = {}
    for spec in EVENTS:
        event = Event(year=YEAR, **spec)
        session.add(event)
        session.flush()
        events[spec["round_number"]] = event

    export_count = load_raw_exports(session, events, results_dir)
    print(f"Stored {export_count} raw exports (licence columns stripped) for rounds {sorted(INCLUDE_ROUNDS)}")

    clubs: dict = {}
    people: dict = {}

    for category, rounds in all_results.items():
        for round_num, rows in rounds.items():
            event = events[int(round_num)]
            for result in rows:
                person = _participant(
                    session,
                    people,
                    clubs,
                    result["last_name"],
                    result["first_name"],
                    result["team"],
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

    seen_norms = set()
    for (raw_last, raw_first), canonical in rider_normalizations.items():
        if (raw_last, raw_first) == canonical:
            continue
        person = people.get(canonical)
        if person is None:
            continue
        categories = {
            category
            for category, rounds in all_results.items()
            for rows in rounds.values()
            for result in rows
            if result["raw_last_name"] == raw_last and result["raw_first_name"] == raw_first
        }
        for category in categories:
            key = (raw_last, raw_first, category, person.id)
            if key in seen_norms:
                continue
            seen_norms.add(key)
            session.add(
                NameNormalisation(
                    participant_id=person.id,
                    raw_last_name=raw_last,
                    raw_first_name=raw_first,
                    category=category,
                )
            )

    for category, riders in category_standings.items():
        for rider in riders:
            person = people[(rider["last_name"], rider["first_name"])]
            club = _club(session, clubs, rider["team"])
            standing = Standing(
                year=YEAR,
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
                        event_id=events[int(round_num)].id,
                        points=points,
                    )
                )

    for team in team_standings:
        club = clubs[team["team"]]
        club_standing = ClubStanding(year=YEAR, club_id=club.id, total_points=team["total"])
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

    session.commit()
    print(
        f"Loaded {YEAR} rounds {sorted(INCLUDE_ROUNDS)}: "
        f"{len(people)} riders, {sum(len(v) for v in category_standings.values())} standings rows"
    )


def _db_rider_rows(session: Session, category: str) -> list[dict]:
    standings = session.scalars(
        select(Standing)
        .where(Standing.year == YEAR, Standing.category == category)
        .order_by(Standing.points_excl_lowest.desc(), Standing.total_points.desc(), Standing.id)
    ).all()
    rows = []
    for position, standing in enumerate(standings, 1):
        rounds = {
            session.get(Event, points.event_id).round_number: points.points
            for points in standing.event_points
        }
        rows.append(
            {
                "position": position,
                "last_name": standing.participant.last_name,
                "first_name": standing.participant.first_name,
                "team": standing.club.name if standing.club else "",
                "rounds": rounds,
                "total": standing.total_points,
                "excl": standing.points_excl_lowest,
            }
        )
    return rows


def _db_team_rows(session: Session) -> list[dict]:
    standings = session.scalars(
        select(ClubStanding)
        .where(ClubStanding.year == YEAR)
        .order_by(ClubStanding.total_points.desc(), ClubStanding.id)
    ).all()
    rows = []
    for position, standing in enumerate(standings, 1):
        by_category = {row.category: row.points for row in standing.category_points}
        points = {}
        for label, source in TEAM_COLUMNS.items():
            if label == "Points":
                points[label] = standing.total_points
            elif isinstance(source, tuple):
                points[label] = sum(by_category.get(key, 0) for key in source)
            else:
                points[label] = by_category.get(source, 0)
        rows.append({"position": position, "team": standing.club.name, "points": points})
    return rows


def _rider_key(row: dict) -> tuple:
    rounds = tuple(sorted((num, points) for num, points in row["rounds"].items() if points is not None))
    return (row["last_name"], row["first_name"], row["team"], rounds, row["total"], row["excl"])


def compare_to_html(session: Session, standings_dir: Path) -> list[str]:
    mismatches = []
    for category, filename in RIDER_FILES.items():
        html_rows = parse_rider_standings((standings_dir / filename).read_text(encoding="utf-8"))
        db_rows = _db_rider_rows(session, category)
        html_keys = [_rider_key(row) for row in html_rows]
        db_keys = [_rider_key(row) for row in db_rows]
        if sorted(html_keys) != sorted(db_keys):
            html_set = set(html_keys)
            db_set = set(db_keys)
            mismatches.append(
                f"{filename}: {len(html_rows)} html rows, {len(db_rows)} db rows, "
                f"{len(html_set - db_set)} only in html, {len(db_set - html_set)} only in db"
            )
            for row in sorted(html_set - db_set)[:8]:
                mismatches.append(f"  html only: {row}")
            for row in sorted(db_set - html_set)[:8]:
                mismatches.append(f"  db only: {row}")
        else:
            html_order = [(row["position"], row["last_name"], row["first_name"]) for row in html_rows]
            db_order = [(row["position"], row["last_name"], row["first_name"]) for row in db_rows]
            if html_order != db_order:
                mismatches.append(f"{filename}: same riders and points, different order")

    html_teams = parse_team_standings((standings_dir / "teams.html").read_text(encoding="utf-8"))
    db_teams = _db_team_rows(session)
    html_team_keys = [(row["team"], tuple(sorted(row["points"].items()))) for row in html_teams]
    db_team_keys = [(row["team"], tuple(sorted(row["points"].items()))) for row in db_teams]
    if sorted(html_team_keys) != sorted(db_team_keys):
        html_set = set(html_team_keys)
        db_set = set(db_team_keys)
        mismatches.append(
            f"teams.html: {len(html_teams)} html rows, {len(db_teams)} db rows, "
            f"{len(html_set - db_set)} only in html, {len(db_set - html_set)} only in db"
        )
        for row in sorted(html_set - db_set)[:8]:
            mismatches.append(f"  html only: {row}")
        for row in sorted(db_set - html_set)[:8]:
            mismatches.append(f"  db only: {row}")
    elif [row["team"] for row in html_teams] != [row["team"] for row in db_teams]:
        mismatches.append("teams.html: same points, different order")
    return mismatches


def run_backfill(
    root: Path,
    db_path: Path,
    results_dir: Path,
    standings_dir: Path,
) -> tuple[list[str], list[str]]:
    """Returns (errors, html_diffs). Errors abort; html_diffs are for comparison only."""
    upgrade_schema(root, db_path)
    factory = create_session_factory(db_path)
    with factory() as session:
        load_season(session, results_dir)
        round_3 = session.scalar(select(Event).where(Event.year == YEAR, Event.round_number == 3))
        result_count = len(round_3.results) if round_3 is not None else 0
        print(f"Round 3 status={round_3.status if round_3 else 'missing'} results={result_count}")
        if result_count:
            return ([f"Round 3 has {result_count} results; it should be empty"], [])
        return ([], compare_to_html(session, standings_dir))


def main() -> int:
    root = ROOT
    results_dir = root / "results" / str(YEAR)
    standings_dir = root / "templates" / "standings" / str(YEAR)
    if not results_dir.is_dir():
        print(f"Missing results directory: {results_dir}", file=sys.stderr)
        return 1

    url = build_sqlite_url()
    db_path = Path(url.removeprefix("sqlite:///"))
    print(f"Database: {db_path}")
    errors, html_diffs = run_backfill(root, db_path, results_dir, standings_dir)
    if errors:
        print("Backfill failed:")
        for line in errors:
            print(line)
        return 1
    if html_diffs:
        print("Loaded OK. Static HTML differs from the database (compare with ?source=db):")
        for line in html_diffs:
            print(line)
        return 0
    print("Standings match templates/standings/2026/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
