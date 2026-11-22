from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.participants.data.models import NameNormalisation
    from app.results.data.models import Result, ResultExport
    from app.standings.data.models import EventPoints


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("year", "round_number", name="uq_events_year_round"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    event_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    british_cycling_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    photos_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    results: Mapped[List["Result"]] = relationship(back_populates="event")
    result_exports: Mapped[List["ResultExport"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    event_points: Mapped[List["EventPoints"]] = relationship(back_populates="event")
    name_normalisations: Mapped[List["NameNormalisation"]] = relationship(
        back_populates="event",
    )