from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.events.data.models import Event
    from app.participants.data.models import Club, Participant


class ResultExport(Base):
    """CrossMgr file body as CSV text (licence columns already removed)."""

    __tablename__ = "result_exports"
    __table_args__ = (
        UniqueConstraint("event_id", "filename", name="uq_result_exports_event_filename"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    csv_text: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ingest_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="stored",
        server_default="stored",
    )
    previous_csv_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    event: Mapped["Event"] = relationship(back_populates="result_exports")
    versions: Mapped[List["ResultExportVersion"]] = relationship(
        back_populates="export",
        cascade="all, delete-orphan",
    )


class ResultExportVersion(Base):
    """One stored CSV body for an export. Version 1 is the original upload."""

    __tablename__ = "result_export_versions"
    __table_args__ = (
        UniqueConstraint(
            "export_id",
            "version",
            name="uq_result_export_versions_export_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    export_id: Mapped[int] = mapped_column(
        ForeignKey("result_exports.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    csv_text: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    export: Mapped["ResultExport"] = relationship(back_populates="versions")


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (
        CheckConstraint("dnf = 0 OR points = 0", name="ck_results_dnf_zero_points"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    participant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    club_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    raw_first_name: Mapped[str] = mapped_column(String, nullable=False)
    raw_last_name: Mapped[str] = mapped_column(String, nullable=False)
    raw_club: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dnf: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category_detail: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bib: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gap: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lap_times: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)

    event: Mapped["Event"] = relationship(back_populates="results")
    participant: Mapped[Optional["Participant"]] = relationship(back_populates="results")
    club: Mapped[Optional["Club"]] = relationship(back_populates="results")