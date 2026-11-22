"""name rules tables

Revision ID: e3b1c9027f10
Revises: c7e2a91b4f30
Create Date: 2026-11-22 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.participants.data.seed_rules import PREDEFINED_CLUB_RULES, PREDEFINED_RIDER_RULES

revision: str = "e3b1c9027f10"
down_revision: Union[str, None] = "c7e2a91b4f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rider_name_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_last_name", sa.String(), nullable=False),
        sa.Column("raw_first_name", sa.String(), nullable=False),
        sa.Column("canonical_last_name", sa.String(), nullable=False),
        sa.Column("canonical_first_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), server_default="", nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(datetime('now'))"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("rider_name_rules", schema=None) as batch_op:
        batch_op.create_index(
            "uq_rider_rule_global",
            ["raw_last_name", "raw_first_name", "category"],
            unique=True,
            sqlite_where=sa.text("event_id IS NULL"),
        )
        batch_op.create_index(
            "uq_rider_rule_event",
            ["raw_last_name", "raw_first_name", "category", "event_id"],
            unique=True,
            sqlite_where=sa.text("event_id IS NOT NULL"),
        )

    op.create_table(
        "club_name_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_name", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(datetime('now'))"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("club_name_rules", schema=None) as batch_op:
        batch_op.create_index("uq_club_rule_raw", ["raw_name"], unique=True)

    bind = op.get_bind()
    for raw, canonical, category in PREDEFINED_RIDER_RULES:
        bind.execute(
            sa.text(
                """
                INSERT INTO rider_name_rules (
                    raw_last_name, raw_first_name,
                    canonical_last_name, canonical_first_name,
                    category, source
                ) VALUES (
                    :raw_last, :raw_first,
                    :canon_last, :canon_first,
                    :category, 'predefined'
                )
                """
            ),
            {
                "raw_last": raw[0],
                "raw_first": raw[1],
                "canon_last": canonical[0],
                "canon_first": canonical[1],
                "category": category or "",
            },
        )

    for raw_name, canonical_name in PREDEFINED_CLUB_RULES:
        bind.execute(
            sa.text(
                """
                INSERT INTO club_name_rules (raw_name, canonical_name, source)
                VALUES (:raw_name, :canonical_name, 'predefined')
                """
            ),
            {"raw_name": raw_name, "canonical_name": canonical_name},
        )


def downgrade() -> None:
    op.drop_table("club_name_rules")
    op.drop_table("rider_name_rules")