from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_engine_for_path, create_session_factory
from app.events.data.models import Event
from app.participants.data.models import Club, ClubMembership, NameNormalisation, Participant
from app.results.data.models import Result
from app.standings.data.models import ClubCategoryPoints, ClubStanding, EventPoints, Standing
from app.users.data.models import User


class UserFactory(SQLAlchemyFactory[User]):
    __model__ = User


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.sqlite3"


@pytest.fixture
def session(db_path: Path) -> Session:
    # Setup:
    root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_cfg, "head")
    factory = create_session_factory(db_path)
    with factory() as sess:
        yield sess


def test_migration_creates_all_tables(session: Session) -> None:
    # Run:
    names = set(Base.metadata.tables.keys())
    # Check:
    assert {
        "users",
        "events",
        "clubs",
        "participants",
        "club_memberships",
        "name_normalisations",
        "results",
        "standings",
        "event_points",
        "club_standings",
        "club_category_points",
    }.issubset(names)


def test_user_round_trip(session: Session) -> None:
    # Setup:
    user = UserFactory.build(email="admin@example.com", password_hash="hash")
    # Run:
    session.add(user)
    session.commit()
    loaded = session.get(User, user.id)
    # Check:
    assert loaded is not None
    assert loaded.email == "admin@example.com"


def test_event_unique_year_round(session: Session) -> None:
    # Setup:
    session.add(Event(year=2026, round_number=1, name="Round 1"))
    session.commit()
    session.add(Event(year=2026, round_number=1, name="Duplicate"))
    # Run:
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_one_open_club_membership(session: Session) -> None:
    # Setup:
    club_a = Club(name="ActivCycles")
    club_b = Club(name="Condor")
    participant = Participant(first_name="Jo", last_name="Bloggs")
    session.add_all([club_a, club_b, participant])
    session.commit()
    session.add(
        ClubMembership(
            participant_id=participant.id,
            club_id=club_a.id,
            joined_on=date(2026, 1, 1),
        )
    )
    session.commit()
    # Run:
    session.add(
        ClubMembership(
            participant_id=participant.id,
            club_id=club_b.id,
            joined_on=date(2026, 6, 1),
        )
    )
    # Check:
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_name_normalisation_scopes(session: Session) -> None:
    # Setup:
    participant = Participant(first_name="Oliver", last_name="Bradford")
    event = Event(year=2026, round_number=2)
    session.add_all([participant, event])
    session.commit()
    session.add(
        NameNormalisation(
            participant_id=participant.id,
            raw_first_name="OLLIE",
            raw_last_name="BRADFORD",
            category="v40",
            event_id=None,
        )
    )
    session.add(
        NameNormalisation(
            participant_id=participant.id,
            raw_first_name="OLLIE",
            raw_last_name="BRADFORD",
            category="v40",
            event_id=event.id,
        )
    )
    # Run:
    session.commit()
    rows = session.scalars(select(NameNormalisation)).all()
    # Check:
    assert len(rows) == 2


def test_result_dnf_zero_points(session: Session) -> None:
    # Setup:
    event = Event(year=2026, round_number=1)
    session.add(event)
    session.commit()
    ok = Result(
        event_id=event.id,
        category="Senior Open",
        raw_first_name="A",
        raw_last_name="B",
        position=None,
        dnf=True,
        points=0,
    )
    bad = Result(
        event_id=event.id,
        category="Senior Open",
        raw_first_name="C",
        raw_last_name="D",
        position=None,
        dnf=True,
        points=50,
    )
    session.add(ok)
    session.commit()
    session.add(bad)
    # Run:
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_standing_event_points_polyfactory(session: Session) -> None:
    # Setup:
    club = Club(name="Test Club")
    participant = Participant(first_name="Sam", last_name="Rider")
    event = Event(year=2026, round_number=1, name="Sandwich")
    session.add_all([club, participant, event])
    session.commit()
    participant.club_id = club.id
    session.commit()
    standing = Standing(
        year=2026,
        category="v40",
        participant_id=participant.id,
        club_id=club.id,
        total_points=100,
        points_excl_lowest=94,
    )
    session.add(standing)
    session.commit()
    session.add(EventPoints(standing_id=standing.id, event_id=event.id, points=100))
    session.commit()
    # Run:
    loaded = session.scalar(
        select(EventPoints).where(EventPoints.standing_id == standing.id)
    )
    # Check:
    assert loaded is not None
    assert loaded.points == 100


def test_club_standing_category_points(session: Session) -> None:
    # Setup:
    club = Club(name="EK Velo")
    session.add(club)
    session.commit()
    club_standing = ClubStanding(year=2026, club_id=club.id, total_points=250)
    session.add(club_standing)
    session.commit()
    session.add(ClubCategoryPoints(club_standing_id=club_standing.id, category="womens", points=80))
    session.commit()
    # Run:
    row = session.scalar(select(ClubCategoryPoints))
    # Check:
    assert row is not None
    assert row.category == "womens"