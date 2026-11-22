"""Backfill writes this season and matches the published standings HTML."""

from pathlib import Path

import pytest

from app.standings.domain.html_standings import parse_rider_standings, parse_team_standings

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "2026"


def test_parse_rider_standings_blank_round():
    # Setup:
    html = """
    <table>
      <tr><td>Position</td><td>Last Name</td><td>First Name</td><td>Team</td><td>Category</td>
          <td>1</td><td>2</td><td>Points</td></tr>
      <tr><td>1</td><td>BEAUMONT</td><td>Claire</td><td>ViCiOUS VELO</td><td>Ma40</td>
          <td>100</td><td><br></td><td>100</td></tr>
    </table>
    """
    # Run:
    rows = parse_rider_standings(html)
    # Check:
    assert rows == [
        {
            "position": 1,
            "last_name": "BEAUMONT",
            "first_name": "Claire",
            "team": "ViCiOUS VELO",
            "rounds": {1: 100, 2: None},
            "total": 100,
            "excl": 100,
        }
    ]


def test_parse_team_standings_blank_is_zero():
    # Setup:
    html = """
    <table>
      <tr><td>Position</td><td>Team</td><td>Women</td><td>V40</td><td>Points</td></tr>
      <tr><td>1</td><td>VC Deal</td><td><br></td><td>90</td><td>90</td></tr>
    </table>
    """
    # Run:
    rows = parse_team_standings(html)
    # Check:
    assert rows[0]["team"] == "VC Deal"
    assert rows[0]["points"] == {"Women": 0, "V40": 90, "Points": 90}


@pytest.mark.skipif(not RESULTS.is_dir(), reason="result exports are local only")
def test_backfill_diff_against_published_standings(tmp_path: Path):
    # Setup:
    from scripts.backfill_season import run_backfill

    db_path = tmp_path / "season.sqlite3"
    # Run:
    errors, html_diffs = run_backfill(
        ROOT,
        db_path,
        RESULTS,
        ROOT / "templates" / "standings" / "2026",
    )
    # Check: static HTML lags normalisation, zeros, and round 3 data in the DB.
    assert errors == []
    summaries = [line for line in html_diffs if not line.startswith("  ")]
    assert summaries == [
        "womens.html: 14 html rows, 15 db rows, 6 only in html, 7 only in db",
        "v40.html: 62 html rows, 70 db rows, 29 only in html, 37 only in db",
        "v50.html: 47 html rows, 56 db rows, 26 only in html, 35 only in db",
        "youth.html: 17 html rows, 20 db rows, 13 only in html, 16 only in db",
        "u12.html: 31 html rows, 36 db rows, 17 only in html, 22 only in db",
        "teams.html: 41 html rows, 47 db rows, 25 only in html, 31 only in db",
    ]