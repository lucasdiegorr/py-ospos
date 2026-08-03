"""seed default payment methods

Revision ID: d90ba873eb65
Revises: dfb180779d21
Create Date: 2026-08-03 14:40:00.000000
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from alembic import op
from sqlalchemy import text

revision: str = "d90ba873eb65"
down_revision: str | None = "dfb180779d21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The four default payment methods offered at checkout.
_DEFAULT_METHODS: tuple[tuple[str, str], ...] = (
    ("cash", "Cash"),
    ("card", "Card"),
    ("pix", "PIX"),
    ("fiado", "Fiado"),
)


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(UTC)
    for method_id, name in _DEFAULT_METHODS:
        conn.execute(
            text(
                "INSERT INTO payment_methods (id, name, is_enabled, created_at) "
                "VALUES (:id, :name, TRUE, :created_at) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": method_id, "name": name, "created_at": now},
        )


def downgrade() -> None:
    op.execute("DELETE FROM payment_methods WHERE id IN ('cash', 'card', 'pix', 'fiado')")
