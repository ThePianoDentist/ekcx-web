from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.data.models import Event
from app.results.data.models import ResultExport

INGEST_STATUS_STORED = "stored"


def find_event(session: Session, year: int, round_number: int) -> Optional[Event]:
    return session.scalar(
        select(Event).where(Event.year == year, Event.round_number == round_number)
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
        existing.csv_text = csv_text
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
    return row