from __future__ import annotations

import importlib
from io import StringIO
from pathlib import Path
from time import sleep

import pandas as pd
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import session as db_session
from app.events.data.models import Event
from app.results.data.models import ResultExport


@pytest.fixture
def admin_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Setup:
    db_path = tmp_path / "test.sqlite3"
    results_root = tmp_path / "results"
    results_root.mkdir()
    monkeypatch.setenv("EKCX_DB_PATH", str(db_path))
    monkeypatch.setenv("EKCX_RESULTS_ROOT", str(results_root))
    db_session._session_factory = None

    root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_cfg, "head")

    factory = db_session.create_session_factory(db_path)
    with factory() as session:
        session.add(
            Event(
                year=2026,
                round_number=1,
                name="Round 1: Test",
                status="completed",
            )
        )
        session.commit()

    import main

    importlib.reload(main)
    yield results_root, db_path
    db_session._session_factory = None


@pytest.fixture
def client(admin_env):
  # Setup:
    _results_root, _db_path = admin_env
    import main

    return TestClient(main.app)


def test_upload_stores_disk_and_db(client: TestClient, admin_env):
    # Setup:
    results_root, _ = admin_env
    csv_body = "Pos,License,Last Name\n1,123456,HURST\n"
    # Run:
    response = client.post(
        "/admin/results/upload",
        data={"year": "2026", "round_number": "1"},
        files={"file": ("mens.csv", csv_body.encode(), "text/csv")},
        follow_redirects=False,
    )
    # Check:
    assert response.status_code == 303
    assert (results_root / "2026" / "1" / "mens.csv").is_file()
    factory = db_session.create_session_factory()
    with factory() as session:
        export = session.scalar(
            select(ResultExport).where(ResultExport.filename == "mens.csv")
        )
        assert export is not None
        assert export.uploaded_at is not None
        df = pd.read_csv(StringIO(export.csv_text))
        assert "License" not in df.columns
    list_resp = client.get("/admin/results/?year=2026")
    assert list_resp.status_code == 200
    assert "mens.csv" in list_resp.text


def test_upload_without_event_returns_error(client: TestClient, admin_env):
    # Setup:
    csv_body = "Pos,Last Name\n1,HURST\n"
    # Run:
    response = client.post(
        "/admin/results/upload",
        data={"year": "2026", "round_number": "9"},
        files={"file": ("orphan.csv", csv_body.encode(), "text/csv")},
    )
    # Check:
    assert response.status_code == 400
    assert "No event" in response.text


def test_replace_upload_updates_csv_and_timestamp(client: TestClient, admin_env):
    # Setup:
    csv_v1 = "Pos,Last Name\n1,ONE\n"
    csv_v2 = "Pos,Last Name\n1,TWO\n"
    client.post(
        "/admin/results/upload",
        data={"year": "2026", "round_number": "1"},
        files={"file": ("race.csv", csv_v1.encode(), "text/csv")},
    )
    factory = db_session.create_session_factory()
    with factory() as session:
        first = session.scalar(select(ResultExport).where(ResultExport.filename == "race.csv"))
        assert first is not None
        first_time = first.uploaded_at
    sleep(0.02)
    # Run:
    client.post(
        "/admin/results/upload",
        data={"year": "2026", "round_number": "1"},
        files={"file": ("race.csv", csv_v2.encode(), "text/csv")},
    )
    # Check:
    with factory() as session:
        second = session.scalar(select(ResultExport).where(ResultExport.filename == "race.csv"))
        assert second is not None
        assert "TWO" in second.csv_text
        assert second.uploaded_at is not None
        assert second.uploaded_at >= first_time
        n = session.scalar(
            select(func.count())
            .select_from(ResultExport)
            .where(ResultExport.filename == "race.csv")
        )
        assert n == 1