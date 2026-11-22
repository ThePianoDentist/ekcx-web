"""Standings source: static HTML templates vs SQLite."""

from __future__ import annotations

import os

# From 2026, seniors share the Masters 40 table; SQLite holds this season.
CURRENT_DB_STANDINGS_FROM_YEAR = 2026


def is_staging_site() -> bool:
    raw = os.environ.get("EKCX_STAGING", "").strip().lower()
    return raw in ("1", "true", "yes")


def default_standings_source(year: int) -> str:
    if year >= CURRENT_DB_STANDINGS_FROM_YEAR and is_staging_site():
        return "db"
    return "static"


def resolve_standings_source(year: int, query: str | None) -> str:
    if query is not None:
        return query
    return default_standings_source(year)


def uses_database(year: int, source: str) -> bool:
    return year >= CURRENT_DB_STANDINGS_FROM_YEAR and source == "db"


def standings_nav_query(year: int, source: str) -> str:
    """Keep category/year links on the same source (omit query when it matches default)."""
    if year < CURRENT_DB_STANDINGS_FROM_YEAR:
        return ""
    default = default_standings_source(year)
    if source == "db":
        return "" if default == "db" else "?source=db"
    return "?source=static" if default == "db" else ""