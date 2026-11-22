from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.results.data import repository
from app.results.data.models import ResultExport
from app.results.data.paths import get_results_root
from app.results.domain.category_from_filename import determine_category_from_filename
from app.results.domain.raw_export import file_to_sanitized_csv, round_export_paths

ALLOWED_SUFFIXES = {".csv", ".xlsx"}


class ExportError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def safe_filename(name: str) -> str:
    base = Path(name).name
    if not base or base != name.strip() or ".." in name:
        raise ExportError("Invalid filename")
    suffix = Path(base).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ExportError("File must be .csv or .xlsx")
    return base


def standings_category_for_filename(filename: str) -> Optional[str]:
    """League standings page for this export, when the filename names a category."""
    category = determine_category_from_filename(filename)
    if category in {"skip", "unknown"}:
        return None
    return category


_RACE_LABELS = {
    "womens": "Women",
    "u12": "Under 12",
    "youth": "Youth",
    "v50": "Masters 50",
    "v40": "Masters 40",
    "mens": "Senior",
}


def race_label(category: str) -> str:
    return _RACE_LABELS.get(category, category)


def next_upload_round(session: Session, year: int) -> int:
    """One past the latest round that already has any file, even if a category is missing."""
    latest = repository.latest_uploaded_round(session, year)
    if latest is None:
        return 1
    return latest + 1


def other_file_for_same_race(
    session: Session,
    event_id: int,
    filename: str,
) -> Optional[ResultExport]:
    """A different file already stored for this round and race. The same filename is a replace."""
    category = determine_category_from_filename(filename)
    if category in {"skip", "unknown"}:
        return None
    for row in repository.exports_for_event(session, event_id):
        if row.filename == filename:
            continue
        if determine_category_from_filename(row.filename) == category:
            return row
    return None


def duplicate_race_message(
    session: Session,
    event_id: int,
    filename: str,
    round_number: int,
) -> Optional[str]:
    other = other_file_for_same_race(session, event_id, filename)
    if other is None:
        return None
    label = race_label(determine_category_from_filename(filename))
    return f"Round {round_number} already has a {label} file ({other.filename})."


@dataclass(frozen=True)
class ExportListingRow:
    round_number: int
    filename: str
    on_disk: bool
    in_db: bool
    export_id: Optional[int]
    uploaded_at: Optional[datetime]
    ingest_status: Optional[str]
    event_name: Optional[str]
    standings_category: Optional[str]
    original_version: Optional[int] = None
    latest_version: Optional[int] = None


def versioned_csv_filename(filename: str, version: int) -> str:
    return f"{Path(filename).stem}.v{version}.csv"


def list_exports_for_season(
    session: Session,
    year: int,
    results_root: Optional[Path] = None,
) -> list[ExportListingRow]:
    root = results_root or get_results_root()
    db_rows = repository.list_exports_for_year(session, year)
    bounds = repository.csv_version_bounds(session, [export.id for export, _event in db_rows])
    by_key: dict[tuple[int, str], ExportListingRow] = {}

    for export, event in db_rows:
        original_version, latest_version = bounds.get(export.id, (None, None))
        key = (event.round_number, export.filename)
        by_key[key] = ExportListingRow(
            round_number=event.round_number,
            filename=export.filename,
            on_disk=False,
            in_db=True,
            export_id=export.id,
            uploaded_at=export.uploaded_at,
            ingest_status=export.ingest_status,
            event_name=event.name,
            standings_category=standings_category_for_filename(export.filename),
            original_version=original_version,
            latest_version=latest_version,
        )

    season_dir = root / str(year)
    round_numbers = {row.round_number for row in by_key.values()}
    if season_dir.is_dir():
        for item in season_dir.iterdir():
            if item.is_dir() and item.name.isdigit():
                round_numbers.add(int(item.name))

    for round_num in sorted(round_numbers):
        for path in round_export_paths(season_dir, round_num):
            key = (round_num, path.name)
            on_disk = path.is_file()
            if key in by_key:
                row = by_key[key]
                by_key[key] = ExportListingRow(
                    round_number=row.round_number,
                    filename=row.filename,
                    on_disk=on_disk,
                    in_db=row.in_db,
                    export_id=row.export_id,
                    uploaded_at=row.uploaded_at,
                    ingest_status=row.ingest_status,
                    event_name=row.event_name,
                    standings_category=row.standings_category,
                    original_version=row.original_version,
                    latest_version=row.latest_version,
                )
            else:
                by_key[key] = ExportListingRow(
                    round_number=round_num,
                    filename=path.name,
                    on_disk=on_disk,
                    in_db=False,
                    export_id=None,
                    uploaded_at=None,
                    ingest_status=None,
                    event_name=None,
                    standings_category=standings_category_for_filename(path.name),
                )

    return sorted(by_key.values(), key=lambda r: (r.round_number, r.filename))


def store_export_from_path(
    session: Session,
    event_id: int,
    path: Path,
) -> Optional[ResultExport]:
    csv_text = file_to_sanitized_csv(path)
    if not csv_text:
        return None
    return repository.upsert_export(session, event_id, path.name, csv_text)


def store_upload(
    session: Session,
    year: int,
    round_number: int,
    filename: str,
    data: bytes,
    results_root: Optional[Path] = None,
) -> ResultExport:
    root = results_root or get_results_root()
    name = safe_filename(filename)
    event = repository.find_event(session, year, round_number)
    if event is None:
        raise ExportError(
            f"No event for {year} round {round_number}. Run db-backfill or add the event first."
        )

    dest_dir = root / str(year) / str(round_number)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / name
    dest_path.write_bytes(data)

    csv_text = file_to_sanitized_csv(dest_path)
    if not csv_text:
        dest_path.unlink(missing_ok=True)
        raise ExportError("File is empty or not a valid CrossMgr export after sanitizing")

    return repository.upsert_export(session, event.id, name, csv_text)