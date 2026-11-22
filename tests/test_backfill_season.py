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
    # Check: pages were built before DNF rows scored zero and before two name fixes.
    assert errors == []
    assert html_diffs == [
        "womens.html: 14 html rows, 14 db rows, 1 only in html, 1 only in db",
        "  html only: ('CALEIA-RAMOS', 'Natasha', 'ASSOS UK Racing Team', ((2, 80),), 80, 80)",
        "  db only: ('CALDAR-RAMOS', 'Natasha', 'ASSOS UK Racing Team', ((2, 80),), 80, 80)",
        "v40.html: 62 html rows, 63 db rows, 2 only in html, 3 only in db",
        "  html only: ('DEWILDE-GREY', 'Adam', '', ((2, 43),), 43, 43)",
        "  html only: ('SELMES', 'Daniel', '', ((1, 38), (2, 41)), 79, 79)",
        "  db only: ('BRYAN', 'Ross', 'VC Deal', ((2, 0),), 0, 0)",
        "  db only: ('DE WILDE-GREY', 'Adam', '', ((2, 43),), 43, 43)",
        "  db only: ('SELMES', 'Daniel', 'Lewes', ((1, 38), (2, 41)), 79, 79)",
        "v50.html: 47 html rows, 47 db rows, 2 only in html, 2 only in db",
        "  html only: ('CHARLTON', 'Perrin', 'Hythe Cycling Club', ((2, 83),), 83, 83)",
        "  html only: ('MARSH', 'Nick', 'GS Invicta-ELO-Herberts Cycles', ((1, 59),), 59, 59)",
        "  db only: ('CHARLTON', 'Perrin', 'Hythe Cycling Club', ((1, 0), (2, 83)), 83, 83)",
        "  db only: ('MARSH', 'Nick', 'GS Invicta-ELO-Herberts Cycles', ((1, 59), (2, 0)), 59, 59)",
        "u12.html: 31 html rows, 31 db rows, 2 only in html, 2 only in db",
        "  html only: ('SHEARWOOD', 'Woody', 'Limited Edition Cycling', ((2, 76),), 76, 76)",
        "  html only: ('WHITTLE', 'Monty', 'VC Deal', ((2, 63),), 63, 63)",
        "  db only: ('SHEARWOOD', 'Woody', 'Limited Edition Cycling', ((1, 0), (2, 76)), 76, 76)",
        "  db only: ('WHITTLE', 'Monty', 'VC Deal', ((1, 0), (2, 63)), 63, 63)",
        "teams.html: 41 html rows, 42 db rows, 0 only in html, 1 only in db",
        "  db only: ('Lewes', (('Points', 79), ('Under 12', 0), ('Under 16', 0), ('V40', 79), ('V50', 0), ('Women', 0)))",
    ]
