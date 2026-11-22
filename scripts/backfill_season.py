#!/usr/bin/env python3
"""Load the current season into SQLite and check it against the standings HTML.

2026 rounds 1–3 from disk; round 4+ left for admin upload tests.
Older seasons stay on the static HTML pages. Re-running replaces this season.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.env import load_local_env

load_local_env()

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import build_sqlite_url, create_session_factory
from app.events.data.models import Event
from app.results.data import repository
from app.results.domain.collect_exports import collect_results_from_exports
from app.results.domain.exports import store_export_from_path
from app.results.domain.raw_export import round_export_paths
from app.standings.data.models import ClubStanding, Standing
from app.standings.domain.html_standings import parse_rider_standings, parse_team_standings
from app.standings.domain.persist_season import persist_season_results

YEAR = 2026
INCLUDE_ROUNDS = {1, 2, 3}
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
        "status": "completed",
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
    from app.participants.data.models import Club, ClubMembership, NameNormalisation, Participant
    from app.results.data.models import Result, ResultExport
    from app.standings.data.models import ClubCategoryPoints, ClubStanding, EventPoints, Standing

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


def _skip_disk_export(path: Path) -> bool:
    """QA fixtures in results/2026/* should not replace league rows on backfill."""
    return path.name.startswith("qa-")


def load_raw_exports(
    session: Session,
    events: dict[int, Event],
    results_dir: Path,
) -> int:
    stored = 0
    for round_num in sorted(INCLUDE_ROUNDS):
        event = events[round_num]
        for path in round_export_paths(results_dir, round_num):
            if _skip_disk_export(path):
                continue
            row = store_export_from_path(session, event.id, path)
            if row is None:
                print(f"Skipping empty export: {path.name}", file=sys.stderr)
                continue
            stored += 1
    return stored


def _results_for_included_rounds(
    all_results: dict[str, dict[str, list]],
) -> dict[str, dict[str, list]]:
    filtered: dict[str, dict[str, list]] = {}
    for category, rounds in all_results.items():
        kept = {
            round_key: rows
            for round_key, rows in rounds.items()
            if int(round_key) in INCLUDE_ROUNDS
        }
        if kept:
            filtered[category] = kept
    return filtered


def load_season(session: Session, results_dir: Path) -> None:
    clear_league(session)
    events: dict[int, Event] = {}
    for spec in EVENTS:
        event = Event(year=YEAR, **spec)
        session.add(event)
        session.flush()
        events[spec["round_number"]] = event

    export_count = load_raw_exports(session, events, results_dir)
    print(f"Stored {export_count} raw exports (licence columns stripped) for rounds {sorted(INCLUDE_ROUNDS)}")

    repository.mark_exports_ingested(session, YEAR)
    all_results = _results_for_included_rounds(collect_results_from_exports(session, YEAR))

    riders, standings_rows = persist_season_results(
        session,
        YEAR,
        all_results,
        events,
        SEASON_START,
        merge_similar=True,
    )
    session.commit()
    print(
        f"Loaded {YEAR} rounds {sorted(INCLUDE_ROUNDS)}: "
        f"{riders} riders, {standings_rows} standings rows"
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
