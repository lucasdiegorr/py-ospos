"""Customer model.

A customer has minimal required data (name) plus optional identifiers and a
partial/optional address. The fiado (credit) profile lives on the customer:
credit limit (cents), interest rate (percent), and due period (days). At
least one of the three fiado fields must be set when a profile exists; the
outstanding balance is tracked here too.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.domain.idempotency import utcnow


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    cpf: Mapped[str | None] = mapped_column(String(14), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Optional / partial address — all fields may be empty (reference only).
    street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Fiado profile — at least one of these three must be set to have a profile.
    credit_limit_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interest_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    due_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    outstanding_balance_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
