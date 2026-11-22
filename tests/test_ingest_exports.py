from __future__ import annotations

import importlib
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import session as db_session
from app.events.data.models import Event
from app.results.data.models import Result, ResultExport
from app.results.data.repository import INGEST_STATUS_INGESTED
from app.results.domain.race_dataframe import prepare_race_dataframe
from app.standings.data.models import Standing
from app.standings.domain.refresh_from_exports import refresh_season_from_exports
from app.users.data import repository
from app.users.domain.auth import hash_password, normalize_email

ADMIN_EMAIL = "admin@ekcx.test"
ADMIN_PASSWORD = "test-admin-password"

VALID_CSV = (
    "Pos,Last Name,First Name,Team,Category,Gender\n"
    "1,HURST,Ann,VC Deal,Ma40,F\n"
    "2,SMITH,Bob,Deal RC,Ma40,M\n"
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def ingest_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Setup:
    db_path = tmp_path / "test.sqlite3"
    results_root = tmp_path / "results"
    results_root.mkdir()
    monkeypatch.setenv("EKCX_DB_PATH", str(db_path))
    monkeypatch.setenv("EKCX_RESULTS_ROOT", str(results_root))
    monkeypatch.setenv("EKCX_SESSION_SECRET", "test-session-secret-for-pytest-only")
    db_session._session_factory = None

    root = _project_root()
    alembic_cfg = Config(str(root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_cfg, "head")

    factory = db_session.create_session_factory(db_path)
    with factory() as session:
        for rnd in (1, 2):
            session.add(
                Event(
                    year=2026,
                    round_number=rnd,
                    name=f"Round {rnd}",
                    status="completed",
                )
            )
        repository.create_user(
            session,
            normalize_email(ADMIN_EMAIL),
            hash_password(ADMIN_PASSWORD),
        )
        session.commit()

    yield db_path, results_root
    db_session._session_factory = None


def test_prepare_race_dataframe_drops_dns_and_blank_chip():
    # Setup:
    csv = (
        "Pos,Last Name,First Name,Team,Category,Gender\n"
        "DNS,No,Show,Team X,Ma40,M\n"
        "1,,,Ghost Chip,Ma40,M\n"
        "2,JONES,Sam,RC One,Ma40,M\n"
    )
    # Run:
    df = prepare_race_dataframe(pd.read_csv(StringIO(csv)))
    # Check:
    assert len(df) == 1
    assert df.iloc[0]["Last Name"] == "JONES"


def test_refresh_from_exports_builds_standings(ingest_env):
    # Setup:
    db_path, _ = ingest_env
    factory = db_session.create_session_factory(db_path)
    with factory() as session:
        event1 = session.scalar(select(Event).where(Event.round_number == 1))
        session.add(
            ResultExport(
                event_id=event1.id,
                filename="senior_open_r1.csv",
                csv_text=VALID_CSV,
            )
        )
        session.commit()

    # Run:
    with factory() as session:
        riders, standings_rows = refresh_season_from_exports(session, 2026)
        session.commit()

    # Check:
    assert riders == 2
    assert standings_rows >= 1
    with factory() as session:
        export = session.scalar(select(ResultExport))
        assert export is not None
        assert export.ingest_status == INGEST_STATUS_INGESTED
        n_results = session.scalar(select(func.count()).select_from(Result))
        n_standings = session.scalar(
            select(func.count()).select_from(Standing).where(Standing.year == 2026)
        )
        assert n_results == 2
        assert n_standings >= 1


def test_upload_triggers_ingest(ingest_env):
    # Setup:
    _db_path, _results_root = ingest_env
    import main

    importlib.reload(main)
    client = TestClient(main.app)
    login = client.post(
        "/admin/login",
        data={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "next": "/admin/results/",
        },
        follow_redirects=False,
    )
    assert login.status_code == 303

    # Run:
    response = client.post(
        "/admin/results/upload",
        data={"year": "2026", "round_number": "1"},
        files={"file": ("senior_open.csv", VALID_CSV.encode(), "text/csv")},
        follow_redirects=False,
    )

    # Check:
    assert response.status_code == 303
    factory = db_session.create_session_factory()
    with factory() as session:
        standing = session.scalar(
            select(Standing).where(Standing.year == 2026, Standing.category == "mens")
        )
        assert standing is not None
        assert standing.total_points > 0