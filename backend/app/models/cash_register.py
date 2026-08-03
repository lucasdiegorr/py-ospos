"""Cash shift models.

A shift is opened by an attendant with a starting float, accumulates sales
and cash movements (supply/bleed), and closes with a counted amount and a
computed difference. Expected cash = float + cash sales + supplies − bleeds.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.idempotency import utcnow


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attendant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    float_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")  # open | closed
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counted_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    movements: Mapped[list[CashMovement]] = relationship(
        back_populates="shift", cascade="all, delete-orphan"
    )


class CashMovement(Base):
    __tablename__ = "cash_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # supply | bleed
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    shift: Mapped[Shift] = relationship(back_populates="movements")
