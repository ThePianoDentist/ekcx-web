"""result_exports previous_csv_text

Revision ID: f4a8d2016c11
Revises: e3b1c9027f10
Create Date: 2026-11-22 20:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a8d2016c11"
down_revision: Union[str, None] = "e3b1c9027f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("result_exports", schema=None) as batch_op:
        batch_op.add_column(sa.Column("previous_csv_text", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("result_exports", schema=None) as batch_op:
        batch_op.drop_column("previous_csv_text")