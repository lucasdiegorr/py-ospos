"""Sync capability router: idempotent offline-write ingestion and resolution.

The client pushes buffered offline writes to ``POST /sync/ingest``; the
server applies them exactly once per idempotency key. Entries whose operation
fails to apply are surfaced here so a manager can inspect, retry, or resolve
them. ``GET /sync/pending`` exposes the pending count for the pending-sync
notice shown by reporting.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.models.sync import OutboxEntry
from app.services.sync import (
    EntryNotFoundError,
    SyncError,
    UnknownOperationError,
    ingest_payload,
    list_failed_entries,
    pending_sync_count,
    resolve_entry,
    retry_entry,
)

router = APIRouter(tags=["sync"])

DbSession = Annotated[Session, Depends(get_db)]


def _role_dependency(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a role-checked current-user dependency (typed for ``Depends``)."""
    return cast(Callable[..., CurrentUser], require_role(*roles))


attendant_or_higher = _role_dependency(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)
manager_or_higher = _role_dependency(Role.MANAGER, Role.ADMIN)

AttendantDependency = Annotated[CurrentUser, Depends(attendant_or_higher)]
ManagerDependency = Annotated[CurrentUser, Depends(manager_or_higher)]


class SyncIngest(BaseModel):
    """A buffered offline write pushed to the server."""

    idempotency_key: str = Field(min_length=1, max_length=64)
    operation: str = Field(min_length=1, max_length=50)
    payload: dict


class SyncIngestOut(BaseModel):
    """Outcome of an ingest attempt; ``duplicate`` never re-applies."""

    status: str  # accepted | duplicate
    entry_id: int | None


class OutboxEntryOut(BaseModel):
    """An outbox entry as shown to a manager resolving failures."""

    id: int
    idempotency_key: str
    operation: str
    payload: dict
    status: str
    attempts: int
    error: str | None
    created_at: datetime | None
    synced_at: datetime | None


@router.post("/sync/ingest", response_model=SyncIngestOut)
def ingest(
    body: SyncIngest,
    db: DbSession,
    user: AttendantDependency,
) -> SyncIngestOut:
    """Apply a buffered offline write exactly once (any authenticated user)."""
    try:
        outcome, entry = ingest_payload(
            db,
            idempotency_key=body.idempotency_key,
            operation=body.operation,
            payload=body.payload,
        )
    except UnknownOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SyncIngestOut(status=outcome, entry_id=entry.id if entry else None)


@router.get("/sync/pending")
def pending(db: DbSession, user: AttendantDependency) -> dict[str, int]:
    """Count of writes the server has yet to settle (for the pending-sync notice)."""
    return {"pending_count": pending_sync_count(db)}


@router.get("/sync/failures", response_model=list[OutboxEntryOut])
def failures(db: DbSession, user: ManagerDependency) -> list[OutboxEntryOut]:
    """List entries awaiting manual resolution (manager or admin)."""
    return [_outbox_entry_out(e) for e in list_failed_entries(db)]


@router.post("/sync/failures/{entry_id}/retry", response_model=OutboxEntryOut)
def retry(entry_id: int, db: DbSession, user: ManagerDependency) -> OutboxEntryOut:
    """Re-run the handler of a pending or failed entry (manager or admin)."""
    try:
        return _outbox_entry_out(retry_entry(db, entry_id))
    except EntryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SyncError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/sync/failures/{entry_id}/resolve", response_model=OutboxEntryOut)
def resolve(entry_id: int, db: DbSession, user: ManagerDependency) -> OutboxEntryOut:
    """Permanently settle a pending or failed entry (manager or admin)."""
    try:
        return _outbox_entry_out(resolve_entry(db, entry_id))
    except EntryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SyncError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _outbox_entry_out(entry: OutboxEntry) -> OutboxEntryOut:
    return OutboxEntryOut(
        id=entry.id,
        idempotency_key=entry.idempotency_key,
        operation=entry.operation,
        payload=json.loads(entry.payload),
        status=entry.status,
        attempts=entry.attempts,
        error=entry.error,
        created_at=entry.created_at,
        synced_at=entry.synced_at,
    )
