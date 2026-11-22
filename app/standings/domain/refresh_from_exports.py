"""Rebuild parsed results and standings from result_exports."""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.events.data.models import Event
from app.participants.data.models import Club, ClubMembership, Participant
from app.participants.domain.name_normalisation import RiderKey
from app.results.data import repository
from app.results.data.models import Result
from app.results.domain.collect_exports import IngestError, collect_results_from_exports
from app.standings.data.models import ClubCategoryPoints, ClubStanding, EventPoints, Standing
from app.standings.domain.persist_season import persist_season_results


def clear_computed_league(session: Session) -> None:
    """Drop parsed league rows. Keeps events, result_exports, and users."""
    for model in (
        EventPoints,
        ClubCategoryPoints,
        Result,
        ClubMembership,
        Standing,
        ClubStanding,
        Participant,
        Club,
    ):
        session.execute(delete(model))
    session.flush()


def season_start_for_year(events: list[Event], year: int) -> date:
    if events:
        first = min(events, key=lambda event: event.round_number)
        if first.event_date:
            for fmt in ("%B %d, %Y", "%Y-%m-%d"):
                try:
                    from datetime import datetime

                    return datetime.strptime(first.event_date, fmt).date()
                except ValueError:
                    continue
    return date(year, 9, 13)


def refresh_season_from_exports(
    session: Session,
    year: int,
    *,
    stored_rider_rules: dict[RiderKey, RiderKey] | None = None,
    stored_team_rules: dict[str, str] | None = None,
    merge_similar: bool = False,
) -> tuple[int, int]:
    """
    Parse all result_exports for year, replace computed tables, mark ingested.

    Returns (rider_count, standings_row_count).
    """
    events = list(
        session.scalars(select(Event).where(Event.year == year).order_by(Event.round_number))
    )
    if not events:
        raise IngestError(f"No events for {year}. Run db-backfill first.")

    all_results = collect_results_from_exports(session, year)
    has_rows = any(rows for rounds in all_results.values() for rows in rounds.values())
    if not has_rows:
        raise IngestError(f"No parseable results in result_exports for {year}")

    events_by_round = {event.round_number: event for event in events}
    clear_computed_league(session)
    riders, standings_rows = persist_season_results(
        session,
        year,
        all_results,
        events_by_round,
        season_start_for_year(events, year),
        merge_similar=merge_similar,
        stored_rider_rules=stored_rider_rules,
        stored_team_rules=stored_team_rules,
    )
    return riders, standings_rows