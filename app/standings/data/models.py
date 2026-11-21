from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.events.data.models import Event
    from app.participants.data.models import Club, Participant


class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (
        UniqueConstraint(
            "year",
            "category",
            "participant_id",
            name="uq_standings_year_category_participant",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    club_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clubs.id", ondelete="SET NULL"),
        nullable=True,
    )
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points_excl_lowest: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    participant: Mapped["Participant"] = relationship(back_populates="standings")
    club: Mapped[Optional["Club"]] = relationship(back_populates="standings")
    event_points: Mapped[List["EventPoints"]] = relationship(
        back_populates="standing",
        cascade="all, delete-orphan",
    )


class EventPoints(Base):
    __tablename__ = "event_points"
    __table_args__ = (
        UniqueConstraint("standing_id", "event_id", name="uq_event_points_standing_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    standing_id: Mapped[int] = mapped_column(
        ForeignKey("standings.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    standing: Mapped["Standing"] = relationship(back_populates="event_points")
    event: Mapped["Event"] = relationship(back_populates="event_points")


class ClubStanding(Base):
    __tablename__ = "club_standings"
    __table_args__ = (UniqueConstraint("year", "club_id", name="uq_club_standings_year_club"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    club: Mapped["Club"] = relationship()
    category_points: Mapped[List["ClubCategoryPoints"]] = relationship(
        back_populates="club_standing",
        cascade="all, delete-orphan",
    )


class ClubCategoryPoints(Base):
    __tablename__ = "club_category_points"
    __table_args__ = (
        UniqueConstraint(
            "club_standing_id",
            "category",
            name="uq_club_category_points_standing_category",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    club_standing_id: Mapped[int] = mapped_column(
        ForeignKey("club_standings.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    club_standing: Mapped["ClubStanding"] = relationship(back_populates="category_points")