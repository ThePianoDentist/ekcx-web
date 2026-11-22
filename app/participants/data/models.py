from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.events.data.models import Event
    from app.results.data.models import Result
    from app.standings.data.models import Standing


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    participants: Mapped[List["Participant"]] = relationship(back_populates="club")
    memberships: Mapped[List["ClubMembership"]] = relationship(back_populates="club")
    results: Mapped[List["Result"]] = relationship(back_populates="club")
    standings: Mapped[List["Standing"]] = relationship(back_populates="club")


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    club_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clubs.id", ondelete="SET NULL"),
        nullable=True,
    )

    club: Mapped[Optional["Club"]] = relationship(back_populates="participants")
    memberships: Mapped[List["ClubMembership"]] = relationship(back_populates="participant")
    results: Mapped[List["Result"]] = relationship(back_populates="participant")
    standings: Mapped[List["Standing"]] = relationship(back_populates="participant")
    name_normalisations: Mapped[List["NameNormalisation"]] = relationship(
        back_populates="participant",
    )


class ClubMembership(Base):
    __tablename__ = "club_memberships"
    __table_args__ = (
        Index(
            "uq_club_memberships_current",
            "participant_id",
            unique=True,
            sqlite_where=text("left_on IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        nullable=False,
    )
    joined_on: Mapped[date] = mapped_column(Date, nullable=False)
    left_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    participant: Mapped["Participant"] = relationship(back_populates="memberships")
    club: Mapped["Club"] = relationship(back_populates="memberships")


class NameNormalisation(Base):
    __tablename__ = "name_normalisations"
    __table_args__ = (
        Index(
            "uq_name_norm_all_events",
            "raw_first_name",
            "raw_last_name",
            "category",
            "participant_id",
            unique=True,
            sqlite_where=text("event_id IS NULL"),
        ),
        Index(
            "uq_name_norm_single_event",
            "raw_first_name",
            "raw_last_name",
            "category",
            "event_id",
            "participant_id",
            unique=True,
            sqlite_where=text("event_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_first_name: Mapped[str] = mapped_column(String, nullable=False)
    raw_last_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
    )

    participant: Mapped["Participant"] = relationship(back_populates="name_normalisations")
    event: Mapped[Optional["Event"]] = relationship(back_populates="name_normalisations")


class RiderNameRule(Base):
    """Cross-season mapping from raw rider name to canonical name."""

    __tablename__ = "rider_name_rules"
    __table_args__ = (
        Index(
            "uq_rider_rule_global",
            "raw_last_name",
            "raw_first_name",
            "category",
            unique=True,
            sqlite_where=text("event_id IS NULL"),
        ),
        Index(
            "uq_rider_rule_event",
            "raw_last_name",
            "raw_first_name",
            "category",
            "event_id",
            unique=True,
            sqlite_where=text("event_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_last_name: Mapped[str] = mapped_column(String, nullable=False)
    raw_first_name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_last_name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_first_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("(datetime('now'))"),
    )

    event: Mapped[Optional["Event"]] = relationship()


class ClubNameRule(Base):
    """Cross-season mapping from raw club/team string to canonical name."""

    __tablename__ = "club_name_rules"
    __table_args__ = (Index("uq_club_rule_raw", "raw_name", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("(datetime('now'))"),
    )