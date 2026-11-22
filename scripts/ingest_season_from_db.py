#!/usr/bin/env python3
"""Rebuild parsed results and standings from result_exports in SQLite."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import build_sqlite_url, create_session_factory
from app.results.domain.collect_exports import IngestError
from app.standings.domain.refresh_from_exports import refresh_season_from_exports

DEFAULT_YEAR = 2026


def main() -> int:
    year = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_YEAR
    url = build_sqlite_url()
    db_path = Path(url.removeprefix("sqlite:///"))
    print(f"Database: {db_path}")
    factory = create_session_factory(db_path)
    with factory() as session:
        try:
            riders, standings_rows = refresh_season_from_exports(session, year)
            session.commit()
        except IngestError as exc:
            session.rollback()
            print(exc.message, file=sys.stderr)
            return 1
    print(f"Ingested {year}: {riders} riders, {standings_rows} standings rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())