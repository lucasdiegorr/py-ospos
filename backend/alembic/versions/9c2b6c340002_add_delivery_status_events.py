"""add delivery_status_events

Revision ID: 9c2b6c340002
Revises: 8c1a5b230001
Create Date: 2026-08-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9c2b6c340002"
down_revision: str | None = "8c1a5b230001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_status_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("delivery_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_delivery_status_events_delivery_id",
        "delivery_status_events",
        ["delivery_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_status_events_delivery_id", table_name="delivery_status_events")
    op.drop_table("delivery_status_events")
