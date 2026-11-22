"""Render a standings table from SQLite in the same shape as the static pages."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.events.data.models import Event
from app.participants.data.models import Participant
from app.results.data.models import Result
from app.standings.data.models import ClubStanding, EventPoints, Standing
from scripts.generate_standings_2025 import generate_category_html, generate_teams_html

TITLES = {
    "mens": "Senior Open",
    "womens": "Women",
    "youth": "Youth U16/U14",
    "u12": "Under 12",
    "v40": "Veteran 40 Open",
    "v50": "Veteran 50 Open",
}

EMPTY = "<p>No standings in the database for this season yet.</p>"


def render_standings(session: Session, year: int, category: str) -> str:
    if category == "teams":
        return _render_teams(session, year)
    riders = _rider_rows(session, year, category)
    if not riders:
        return EMPTY
    title = TITLES.get(category, category)
    return generate_category_html(category, riders, _max_round(session, year), title)


def _max_round(session: Session, year: int) -> int:
    value = session.scalar(
        select(func.max(Event.round_number))
        .join(Result, Result.event_id == Event.id)
        .where(Event.year == year)
    )
    return int(value or 0)


def _rider_rows(session: Session, year: int, category: str) -> list[dict]:
    standings = session.scalars(
        select(Standing)
        .where(Standing.year == year, Standing.category == category)
        .options(
            selectinload(Standing.participant)
            .selectinload(Participant.results)
            .selectinload(Result.event),
            selectinload(Standing.club),
            selectinload(Standing.event_points).selectinload(EventPoints.event),
        )
        .order_by(
            Standing.points_excl_lowest.desc(),
            Standing.total_points.desc(),
            Standing.id,
        )
    ).all()
    rows = []
    for standing in standings:
        sheet_category, gender = _profile(standing, year, category)
        rows.append(
            {
                "last_name": standing.participant.last_name,
                "first_name": standing.participant.first_name,
                "team": standing.club.name if standing.club else "",
                "category": sheet_category,
                "gender": gender,
                "points_by_round": {
                    points.event.round_number: points.points for points in standing.event_points
                },
                "total_points": standing.total_points,
                "points_excl_lowest": standing.points_excl_lowest,
            }
        )
    return rows


def _profile(standing: Standing, year: int, category: str) -> tuple[str, str]:
    """Sheet category and gender from the earliest result, matching the generator."""
    results = [
        result
        for result in standing.participant.results
        if result.category == category and result.event.year == year
    ]
    results.sort(key=lambda result: (result.event.round_number, result.id))
    if not results:
        return "", ""
    first = results[0]
    return first.category_detail or "", first.gender or ""


def _render_teams(session: Session, year: int) -> str:
    standings = session.scalars(
        select(ClubStanding)
        .where(ClubStanding.year == year)
        .options(
            selectinload(ClubStanding.club),
            selectinload(ClubStanding.category_points),
        )
        .order_by(ClubStanding.total_points.desc(), ClubStanding.id)
    ).all()
    if not standings:
        return EMPTY
    rows = []
    for standing in standings:
        by_category = {row.category: row.points for row in standing.category_points}
        rows.append(
            {
                "team": standing.club.name,
                "womens": by_category.get("womens", 0),
                "mens": by_category.get("mens", 0),
                "u12": by_category.get("u12", 0),
                "youth": by_category.get("youth", 0),
                "v40": by_category.get("v40", 0),
                "v50": by_category.get("v50", 0),
                "total": standing.total_points,
            }
        )
    return generate_teams_html(rows, join_open=year >= 2026)
