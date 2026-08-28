"""add sale cancelled_reason

Revision ID: 8c1a5b230001
Revises: d90ba873eb65
Create Date: 2026-08-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8c1a5b230001"
down_revision: str | None = "d90ba873eb65"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sales", sa.Column("cancelled_reason", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("sales", "cancelled_reason")
