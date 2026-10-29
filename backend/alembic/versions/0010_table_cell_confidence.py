"""add confidence to table_cells

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-23 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("table_cells", sa.Column("confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("table_cells", "confidence")
