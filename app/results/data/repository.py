from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.events.data.models import Event
from app.results.data.models import ResultExport, ResultExportVersion

INGEST_STATUS_STORED = "stored"
INGEST_STATUS_PENDING_REVIEW = "pending_review"
INGEST_STATUS_INGESTED = "ingested"


def find_event(session: Session, year: int, round_number: int) -> Optional[Event]:
    return session.scalar(
        select(Event).where(Event.year == year, Event.round_number == round_number)
    )


def latest_uploaded_round(session: Session, year: int) -> Optional[int]:
    value = session.scalar(
        select(func.max(Event.round_number))
        .select_from(Event)
        .join(ResultExport, ResultExport.event_id == Event.id)
        .where(Event.year == year)
    )
    if value is None:
        return None
    return int(value)


def exports_for_event(session: Session, event_id: int) -> list[ResultExport]:
    return list(
        session.scalars(select(ResultExport).where(ResultExport.event_id == event_id))
    )


def list_exports_for_year(session: Session, year: int) -> list[tuple[ResultExport, Event]]:
    rows = session.execute(
        select(ResultExport, Event)
        .join(Event, ResultExport.event_id == Event.id)
        .where(Event.year == year)
        .order_by(Event.round_number, ResultExport.filename)
    ).all()
    return [(row[0], row[1]) for row in rows]


def get_export(session: Session, export_id: int) -> Optional[ResultExport]:
    return session.get(ResultExport, export_id)


def upsert_export(
    session: Session,
    event_id: int,
    filename: str,
    csv_text: str,
) -> ResultExport:
    existing = session.scalar(
        select(ResultExport).where(
            ResultExport.event_id == event_id,
            ResultExport.filename == filename,
        )
    )
    now = datetime.utcnow()
    if existing is not None:
        if existing.ingest_status == INGEST_STATUS_INGESTED:
            existing.previous_csv_text = existing.csv_text
        record_csv_version(session, existing, csv_text)
        existing.uploaded_at = now
        existing.ingest_status = INGEST_STATUS_STORED
        session.flush()
        return existing
    row = ResultExport(
        event_id=event_id,
        filename=filename,
        csv_text=csv_text,
        uploaded_at=now,
        ingest_status=INGEST_STATUS_STORED,
    )
    session.add(row)
    session.flush()
    record_csv_version(session, row, csv_text)
    return row


def latest_csv_version(session: Session, export_id: int) -> Optional[ResultExportVersion]:
    return session.scalar(
        select(ResultExportVersion)
        .where(ResultExportVersion.export_id == export_id)
        .order_by(ResultExportVersion.version.desc())
        .limit(1)
    )


def get_csv_version(
    session: Session,
    export_id: int,
    version: int,
) -> Optional[ResultExportVersion]:
    return session.scalar(
        select(ResultExportVersion).where(
            ResultExportVersion.export_id == export_id,
            ResultExportVersion.version == version,
        )
    )


def csv_version_bounds(session: Session, export_ids: list[int]) -> dict[int, tuple[int, int]]:
    if not export_ids:
        return {}
    rows = session.execute(
        select(
            ResultExportVersion.export_id,
            func.min(ResultExportVersion.version),
            func.max(ResultExportVersion.version),
        )
        .where(ResultExportVersion.export_id.in_(export_ids))
        .group_by(ResultExportVersion.export_id)
    ).all()
    return {row[0]: (row[1], row[2]) for row in rows}


def record_csv_version(session: Session, export: ResultExport, csv_text: str) -> ResultExportVersion:
    """Keep csv_text as the latest body. Append a version only when the text changes."""
    latest = latest_csv_version(session, export.id)
    if latest is not None and latest.csv_text == csv_text:
        export.csv_text = csv_text
        return latest
    version = 1 if latest is None else latest.version + 1
    row = ResultExportVersion(
        export_id=export.id,
        version=version,
        csv_text=csv_text,
        created_at=datetime.utcnow(),
    )
    export.csv_text = csv_text
    session.add(row)
    session.flush()
    return row


def mark_export_pending_review(session: Session, export: ResultExport) -> None:
    export.ingest_status = INGEST_STATUS_PENDING_REVIEW
    session.flush()


def mark_export_ingested(session: Session, export: ResultExport) -> None:
    export.ingest_status = INGEST_STATUS_INGESTED
    export.previous_csv_text = None
    session.flush()


def mark_exports_ingested(session: Session, year: int) -> None:
    """Mark every export for a season ingested (backfill / scripts)."""
    for export, _event in list_exports_for_year(session, year):
        export.ingest_status = INGEST_STATUS_INGESTED
    session.flush()