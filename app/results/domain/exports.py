from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.results.data import repository
from app.results.data.models import ResultExport
from app.results.data.paths import get_results_root
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


def list_exports_for_season(
    session: Session,
    year: int,
    results_root: Optional[Path] = None,
) -> list[ExportListingRow]:
    root = results_root or get_results_root()
    db_rows = repository.list_exports_for_year(session, year)
    by_key: dict[tuple[int, str], ExportListingRow] = {}

    for export, event in db_rows:
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