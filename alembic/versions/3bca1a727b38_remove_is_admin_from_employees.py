"""remove is_admin from employees

Revision ID: 3bca1a727b38
Revises: b171b4659a5d
Create Date: 2026-06-29 15:19:57.057962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3bca1a727b38"
down_revision: Union[str, None] = "b171b4659a5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("employees", "is_admin")


def downgrade() -> None:
    op.add_column("employees", sa.Column("is_admin", sa.Boolean(), nullable=False))
