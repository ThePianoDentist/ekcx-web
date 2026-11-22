"""result_exports metadata

Revision ID: c7e2a91b4f30
Revises: a9c6bdd31f44
Create Date: 2026-11-22 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e2a91b4f30"
down_revision: Union[str, None] = "a9c6bdd31f44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("result_exports", schema=None) as batch_op:
        batch_op.add_column(sa.Column("uploaded_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column("ingest_status", sa.String(), server_default="stored", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("result_exports", schema=None) as batch_op:
        batch_op.drop_column("ingest_status")
        batch_op.drop_column("uploaded_at")