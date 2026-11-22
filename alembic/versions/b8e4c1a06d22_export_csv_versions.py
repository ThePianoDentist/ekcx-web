"""result export csv versions

Revision ID: b8e4c1a06d22
Revises: f4a8d2016c11
Create Date: 2026-11-22 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e4c1a06d22"
down_revision: Union[str, None] = "f4a8d2016c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "result_export_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("export_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("csv_text", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["export_id"], ["result_exports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "export_id",
            "version",
            name="uq_result_export_versions_export_version",
        ),
    )
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, csv_text, previous_csv_text, uploaded_at FROM result_exports"
        )
    ).fetchall()
    insert = sa.text(
        "INSERT INTO result_export_versions (export_id, version, csv_text, created_at) "
        "VALUES (:export_id, :version, :csv_text, :created_at)"
    )
    for row in rows:
        export_id, csv_text, previous_csv_text, uploaded_at = row
        if previous_csv_text and previous_csv_text != csv_text:
            conn.execute(
                insert,
                {
                    "export_id": export_id,
                    "version": 1,
                    "csv_text": previous_csv_text,
                    "created_at": uploaded_at,
                },
            )
            conn.execute(
                insert,
                {
                    "export_id": export_id,
                    "version": 2,
                    "csv_text": csv_text,
                    "created_at": uploaded_at,
                },
            )
        else:
            conn.execute(
                insert,
                {
                    "export_id": export_id,
                    "version": 1,
                    "csv_text": csv_text,
                    "created_at": uploaded_at,
                },
            )


def downgrade() -> None:
    op.drop_table("result_export_versions")
