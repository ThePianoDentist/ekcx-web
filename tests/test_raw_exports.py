"""Licence stripping and raw export storage."""

from io import StringIO
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import func, select

from app.results.data.models import ResultExport
from app.results.domain.raw_export import (
    file_to_sanitized_csv,
    is_licence_column,
    sanitize_csv_text,
)


def test_is_licence_column_matches_crossmgr_header():
    # Setup:
    # Run:
    # Check:
    assert is_licence_column("License")
    assert is_licence_column("BC Licence")
    assert not is_licence_column("Last Name")


def test_sanitize_csv_text_drops_license_column():
    # Setup:
    original = "Pos,License,Last Name\n1,123456,HURST\n"
    # Run:
    cleaned = sanitize_csv_text(original)
    # Check:
    assert cleaned is not None
    df = pd.read_csv(StringIO(cleaned))
    assert "License" not in df.columns
    assert df.loc[0, "Last Name"] == "HURST"


def test_file_to_sanitized_csv_from_local_xlsx():
    # Setup:
    root = Path(__file__).resolve().parents[1]
    round_dir = root / "results" / "2026" / "1"
    if not round_dir.is_dir():
        pytest.skip("result exports are local only")
    path = next(round_dir.glob("*.xlsx"), None)
    if path is None:
        pytest.skip("no xlsx in round 1")
    # Run:
    csv_text = file_to_sanitized_csv(path)
    # Check:
    assert csv_text
    df = pd.read_csv(StringIO(csv_text))
    assert not any(is_licence_column(column) for column in df.columns)


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "results" / "2026").is_dir(),
    reason="result exports are local only",
)
def test_backfill_stores_exports_for_rounds_one_and_two(tmp_path: Path):
    # Setup:
    from scripts.backfill_season import INCLUDE_ROUNDS, run_backfill

    root = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "season.sqlite3"
    # Run:
    errors, _html_diffs = run_backfill(
        root,
        db_path,
        root / "results" / "2026",
        root / "templates" / "standings" / "2026",
    )
    # Check:
    assert errors == []
    from app.db.session import create_session_factory

    from app.events.data.models import Event

    with create_session_factory(db_path)() as session:
        count = session.scalar(select(func.count()).select_from(ResultExport))
        round_numbers = set(
            session.scalars(
                select(Event.round_number)
                .join(ResultExport, ResultExport.event_id == Event.id)
                .distinct()
            ).all()
        )
    assert count and count > 0
    assert round_numbers == set(INCLUDE_ROUNDS)