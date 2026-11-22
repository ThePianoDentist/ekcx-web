"""2026 standings can be rendered from SQLite without replacing the static pages."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.db.session import create_session_factory
from app.events.data.models import Event
from app.participants.data.models import Club, Participant
from app.results.data.models import Result
from app.standings.data.models import ClubCategoryPoints, ClubStanding, EventPoints, Standing
from app.standings.domain.html_standings import parse_rider_standings, parse_team_standings
from app.standings.domain.render import render_standings
from app.standings.interfaces.web.routes import shows_database


def test_shows_database_only_for_this_season():
    # Setup:
    # Run:
    # Check:
    assert shows_database(2026, "db") is True
    assert shows_database(2026, "static") is False
    assert shows_database(2025, "db") is False


def test_render_standings_from_sqlite(tmp_path: Path):
    # Setup:
    db_path = tmp_path / "standings.sqlite3"
    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")
    session: Session = create_session_factory(db_path)()
    club = Club(name="VC Deal")
    rider = Participant(last_name="HURST", first_name="Cameron", club=club)
    event = Event(year=2026, round_number=1, name="Round 1", status="completed")
    session.add_all([club, rider, event])
    session.flush()
    session.add(
        Result(
            event_id=event.id,
            category="v40",
            participant_id=rider.id,
            club_id=club.id,
            raw_last_name="HURST",
            raw_first_name="Cameron",
            raw_club="VC Deal",
            position=1,
            dnf=False,
            points=100,
            category_detail="Senior",
            gender="Male",
        )
    )
    standing = Standing(
        year=2026,
        category="v40",
        participant_id=rider.id,
        club_id=club.id,
        total_points=100,
        points_excl_lowest=100,
    )
    session.add(standing)
    session.flush()
    session.add(EventPoints(standing_id=standing.id, event_id=event.id, points=100))
    team = ClubStanding(year=2026, club_id=club.id, total_points=100)
    session.add(team)
    session.flush()
    session.add(ClubCategoryPoints(club_standing_id=team.id, category="v40", points=100))
    session.commit()

    # Run:
    rider_html = render_standings(session, 2026, "v40")
    team_html = render_standings(session, 2026, "teams")
    session.close()

    # Check:
    riders = parse_rider_standings(rider_html)
    assert riders[0]["last_name"] == "HURST"
    assert riders[0]["rounds"] == {1: 100}
    assert riders[0]["total"] == 100
    assert "Senior" in rider_html
    teams = parse_team_standings(team_html)
    assert teams[0]["team"] == "VC Deal"
    assert teams[0]["points"]["V40"] == 100
    assert render_standings(create_session_factory(db_path)(), 2026, "youth") == (
        "<p>No standings in the database for this season yet.</p>"
    )
