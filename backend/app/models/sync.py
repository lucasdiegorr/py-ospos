"""Sync models: idempotency records and the outbox.

The client writes to a local outbox while offline; the server records
processed idempotency keys so re-delivery cannot create duplicates, and
queues outbox entries for reconciliation and manual resolution.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.domain.idempotency import utcnow


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    idempotency_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class OutboxEntry(Base):
    __tablename__ = "outbox_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. sale.completed
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON payload
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | synced | failed
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
