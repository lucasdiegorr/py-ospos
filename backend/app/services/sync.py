"""Sync services: idempotent ingestion of offline writes and reconciliation.

The client buffers writes in a local outbox while offline and pushes entries
to the server on reconnect. The server applies each entry exactly once:

- a client-generated idempotency key is recorded (``IdempotencyRecord``) once
  applied, so re-delivery of the same entry is acknowledged without creating a
  second record;
- the entry's payload is applied by an operation handler registered by the
  owning capability (``register_operation``), e.g. ``sale.completed`` by the
  sales capability;
- an entry whose handler fails is kept in the outbox with an ``error`` and
  surfaced to the manager resolution queue instead of being dropped.

Reconciliation rules (see specs/sync/spec.md): stock movements apply in sync
order, so two offline sales of the same product both reduce stock in arrival
order; price-at-sale is preserved, so an offline sale priced before a server
price change is kept as recorded and flagged for review. A manager resolves an
entry that conflicts permanently via ``resolve_entry``.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.idempotency import utcnow
from app.models.sync import IdempotencyRecord, OutboxEntry

# A handler applies a single buffered offline write against the given session.
Handler = Callable[[Session, dict], None]

_OPERATION_HANDLERS: dict[str, Handler] = {}


class SyncError(Exception):
    """Base class for sync domain violations."""


class UnknownOperationError(SyncError):
    """Raised when ingesting an entry whose operation has no handler."""


class EntryNotFoundError(SyncError):
    """Raised when referencing an outbox entry that does not exist."""


def register_operation(operation: str, handler: Handler) -> None:
    """Register a handler that applies a buffered offline write.

    Capabilities call this at import time, e.g. ``register_operation(
    "sale.completed", apply_completed_sale)``.
    """
    _OPERATION_HANDLERS[operation] = handler


def ingest_payload(
    db: Session,
    *,
    idempotency_key: str,
    operation: str,
    payload: dict,
) -> tuple[str, OutboxEntry | None]:
    """Apply a buffered offline write exactly once.

    Returns ``("duplicate", None)`` when the key was already applied or
    resolved and ``("accepted", entry)`` otherwise. The entry is persisted
    before its handler runs so a failing handler leaves it queued for
    reconciliation. Unknown operations are rejected without writing anything.
    """
    if db.get(IdempotencyRecord, idempotency_key) is not None:
        return "duplicate", None
    if operation not in _OPERATION_HANDLERS:
        raise UnknownOperationError(f"Unknown operation: {operation}")
    entry = db.scalar(select(OutboxEntry).where(OutboxEntry.idempotency_key == idempotency_key))
    if entry is None:
        entry = OutboxEntry(
            idempotency_key=idempotency_key,
            operation=operation,
            payload=json.dumps(payload, ensure_ascii=False),
        )
        db.add(entry)
    else:
        # Re-delivery of a key whose previous apply failed: reuse the row.
        entry.operation = operation
        entry.payload = json.dumps(payload, ensure_ascii=False)
    db.commit()
    _apply(db, entry)
    return "accepted", entry


def list_failed_entries(db: Session) -> list[OutboxEntry]:
    """Return outbox entries waiting for manager resolution, oldest first."""
    stmt = select(OutboxEntry).where(OutboxEntry.status == "failed").order_by(OutboxEntry.id)
    return list(db.scalars(stmt))


def retry_entry(db: Session, entry_id: int) -> OutboxEntry:
    """Re-run the handler of a pending or failed entry."""
    entry = _get_entry_or_raise(db, entry_id)
    if entry.status not in ("pending", "failed"):
        raise SyncError(f"Entry {entry_id} is already {entry.status}")
    _apply(db, entry)
    return entry


def resolve_entry(db: Session, entry_id: int) -> OutboxEntry:
    """Permanently settle a pending or failed entry decided by a manager.

    The write is not applied; the idempotency key is recorded so a later
    re-delivery is acknowledged instead of re-entering the queue.
    """
    entry = _get_entry_or_raise(db, entry_id)
    if entry.status not in ("pending", "failed"):
        raise SyncError(f"Entry {entry_id} is already {entry.status}")
    entry.status = "resolved"
    db.add(IdempotencyRecord(idempotency_key=entry.idempotency_key))
    db.commit()
    return entry


def pending_sync_count(db: Session) -> int:
    """Return the number of writes the server has yet to settle."""
    count = db.scalar(
        select(func.count(OutboxEntry.id)).where(OutboxEntry.status.in_(("pending", "failed")))
    )
    return int(count or 0)


def _get_entry_or_raise(db: Session, entry_id: int) -> OutboxEntry:
    entry = db.get(OutboxEntry, entry_id)
    if entry is None:
        raise EntryNotFoundError(f"Unknown outbox entry: {entry_id}")
    return entry


def _apply(db: Session, entry: OutboxEntry) -> None:
    """Run the entry's handler; record success or queue the failure."""
    handler = _OPERATION_HANDLERS.get(entry.operation)
    if handler is None:
        _queue_failure(db, entry, f"Missing handler for operation: {entry.operation}")
        return
    try:
        handler(db, json.loads(entry.payload))
    except Exception as exc:  # domain conflict/failure => reconciliation queue
        _queue_failure(db, entry, str(exc).strip() or exc.__class__.__name__)
        return
    entry.status = "synced"
    entry.synced_at = utcnow()
    entry.error = None
    db.add(IdempotencyRecord(idempotency_key=entry.idempotency_key))
    db.commit()


def _queue_failure(db: Session, entry: OutboxEntry, message: str) -> None:
    db.rollback()  # discard any partial writes from the failed handler
    db.add(entry)
    entry.status = "failed"
    entry.attempts += 1
    entry.error = message[:2000]
    db.commit()
