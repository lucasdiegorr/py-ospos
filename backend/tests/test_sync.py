"""Tests for the sync capability (specs/sync/spec.md)."""

from __future__ import annotations

from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.core.security import CurrentUser, Role
from app.db import Base
from app.models.sync import IdempotencyRecord, OutboxEntry
from app.services import sync as sync_service


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def operation_handlers() -> Generator[dict, None, None]:
    """Expose the handler registry, isolated per test."""
    saved = dict(sync_service._OPERATION_HANDLERS)
    sync_service._OPERATION_HANDLERS.clear()
    yield sync_service._OPERATION_HANDLERS
    sync_service._OPERATION_HANDLERS.clear()
    sync_service._OPERATION_HANDLERS.update(saved)


def make_handler(
    applied: list[str],
    *,
    fail_on: list[str] | None = None,
) -> sync_service.Handler:
    def handler(db: Session, payload: dict) -> None:
        op = str(payload.get("op", "?"))
        if fail_on is not None and op in fail_on:
            raise ValueError(f"boom on {op}")
        applied.append(op)

    return handler


def ingest(
    client: TestClient,
    *,
    key: str,
    operation: str = "op.ping",
    payload: dict | None = None,
) -> dict:
    return client.post(
        "/sync/ingest",
        json={"idempotency_key": key, "operation": operation, "payload": payload or {}},
    ).json()


def _client(
    db_session: Session,
    *,
    role: Role,
) -> Generator[TestClient, None, None]:
    from fastapi import HTTPException

    from app.api.routers.sync import attendant_or_higher, manager_or_higher
    from app.db import get_db
    from app.main import app

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def gate(*allowed: Role) -> Callable[[], CurrentUser]:
        def dependency() -> CurrentUser:
            if role not in allowed:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return CurrentUser(user_id=1, username="tester", role=role)

        return dependency

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[attendant_or_higher] = gate(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)
    app.dependency_overrides[manager_or_higher] = gate(Role.MANAGER, Role.ADMIN)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def manager_client(db_session: Session) -> Generator[TestClient, None, None]:
    yield from _client(db_session, role=Role.MANAGER)


@pytest.fixture()
def attendant_client(db_session: Session) -> Generator[TestClient, None, None]:
    yield from _client(db_session, role=Role.ATTENDANT)


# --- Service: idempotent ingestion -----------------------------------------


def test_ingest_applies_handler_and_acknowledges(
    db_session: Session, operation_handlers: dict
) -> None:
    applied: list[str] = []
    operation_handlers["op.ping"] = make_handler(applied)
    status, entry = sync_service.ingest_payload(
        db_session, idempotency_key="k1", operation="op.ping", payload={"op": "ping"}
    )
    assert status == "accepted"
    assert entry is not None
    db_session.refresh(entry)
    assert entry.status == "synced"
    assert entry.attempts == 0
    assert db_session.get(IdempotencyRecord, "k1") is not None
    assert applied == ["ping"]


def test_ingest_duplicate_key_acknowledged_without_second_record(
    db_session: Session, operation_handlers: dict
) -> None:
    applied: list[str] = []
    operation_handlers["op.ping"] = make_handler(applied)
    sync_service.ingest_payload(
        db_session, idempotency_key="k1", operation="op.ping", payload={"op": "ping"}
    )
    status, entry = sync_service.ingest_payload(
        db_session, idempotency_key="k1", operation="op.ping", payload={"op": "ping"}
    )
    assert status == "duplicate"
    assert entry is None
    assert applied == ["ping"]
    assert len(db_session.scalars(select(OutboxEntry)).all()) == 1
    assert len(db_session.scalars(select(IdempotencyRecord)).all()) == 1


def test_ingest_unknown_operation_rejected(db_session: Session) -> None:
    with pytest.raises(sync_service.UnknownOperationError):
        sync_service.ingest_payload(db_session, idempotency_key="k2", operation="nope", payload={})
    assert sync_service.pending_sync_count(db_session) == 0


def test_handler_failure_queues_entry_for_reconciliation(
    db_session: Session, operation_handlers: dict
) -> None:
    applied: list[str] = []
    operation_handlers["op.fragile"] = make_handler(applied, fail_on=["x"])
    status, entry = sync_service.ingest_payload(
        db_session, idempotency_key="k3", operation="op.fragile", payload={"op": "x"}
    )
    assert status == "accepted"
    assert entry is not None
    db_session.refresh(entry)
    assert entry.status == "failed"
    assert entry.attempts == 1
    assert entry.error is not None
    assert db_session.get(IdempotencyRecord, "k3") is None
    assert sync_service.pending_sync_count(db_session) == 1
    assert [f.id for f in sync_service.list_failed_entries(db_session)] == [entry.id]


def test_pending_count_excludes_synced_and_resolved(
    db_session: Session, operation_handlers: dict
) -> None:
    applied: list[str] = []
    operation_handlers["op.ping"] = make_handler(applied)
    operation_handlers["op.fragile"] = make_handler(applied, fail_on=["x"])
    sync_service.ingest_payload(db_session, idempotency_key="ok", operation="op.ping", payload={})
    assert sync_service.pending_sync_count(db_session) == 0
    _, bad = sync_service.ingest_payload(
        db_session, idempotency_key="bad", operation="op.fragile", payload={"op": "x"}
    )
    assert bad is not None
    assert sync_service.pending_sync_count(db_session) == 1
    sync_service.resolve_entry(db_session, bad.id)
    assert sync_service.pending_sync_count(db_session) == 0


def test_retry_applies_previously_failed_entry(
    db_session: Session, operation_handlers: dict
) -> None:
    applied: list[str] = []
    fail_on = ["x"]
    operation_handlers["op.fragile"] = make_handler(applied, fail_on=fail_on)
    _, entry = sync_service.ingest_payload(
        db_session, idempotency_key="k4", operation="op.fragile", payload={"op": "x"}
    )
    assert entry is not None
    fail_on.clear()
    retried = sync_service.retry_entry(db_session, entry.id)
    assert retried.status == "synced"
    assert applied == ["x"]
    assert db_session.get(IdempotencyRecord, "k4") is not None
    status, later = sync_service.ingest_payload(
        db_session, idempotency_key="k4", operation="op.fragile", payload={"op": "x"}
    )
    assert status == "duplicate"
    assert later is None


def test_resolve_marks_settled_and_dedups_later(
    db_session: Session, operation_handlers: dict
) -> None:
    applied: list[str] = []
    operation_handlers["op.fragile"] = make_handler(applied, fail_on=["x"])
    _, entry = sync_service.ingest_payload(
        db_session, idempotency_key="k5", operation="op.fragile", payload={"op": "x"}
    )
    assert entry is not None
    resolved = sync_service.resolve_entry(db_session, entry.id)
    assert resolved.status == "resolved"
    assert db_session.get(IdempotencyRecord, "k5") is not None
    status, _ = sync_service.ingest_payload(
        db_session, idempotency_key="k5", operation="op.fragile", payload={"op": "x"}
    )
    assert status == "duplicate"


def test_retry_missing_entry_raises(db_session: Session) -> None:
    with pytest.raises(sync_service.EntryNotFoundError):
        sync_service.retry_entry(db_session, 999)


def test_resolve_missing_entry_raises(db_session: Session) -> None:
    with pytest.raises(sync_service.EntryNotFoundError):
        sync_service.resolve_entry(db_session, 999)


# --- Router -----------------------------------------------------------------


def test_ingest_endpoint_accepted(manager_client: TestClient, operation_handlers: dict) -> None:
    operation_handlers["op.ping"] = make_handler([])
    response = manager_client.post(
        "/sync/ingest",
        json={"idempotency_key": "r1", "operation": "op.ping", "payload": {"op": "ping"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert isinstance(body["entry_id"], int)


def test_ingest_endpoint_duplicate(manager_client: TestClient, operation_handlers: dict) -> None:
    operation_handlers["op.ping"] = make_handler([])
    first = ingest(manager_client, key="r1", payload={"op": "ping"})
    second = ingest(manager_client, key="r1", payload={"op": "ping"})
    assert first["status"] == "accepted"
    assert second == {"status": "duplicate", "entry_id": None}


def test_ingest_endpoint_unknown_operation_is_400(manager_client: TestClient) -> None:
    response = manager_client.post(
        "/sync/ingest",
        json={"idempotency_key": "r3", "operation": "nope", "payload": {}},
    )
    assert response.status_code == 400


def test_ingest_endpoint_validates_required_fields(manager_client: TestClient) -> None:
    response = manager_client.post("/sync/ingest", json={"operation": "op.ping", "payload": {}})
    assert response.status_code == 422


def test_pending_endpoint_counts_failed_entries(
    manager_client: TestClient, operation_handlers: dict
) -> None:
    operation_handlers["op.fragile"] = make_handler([], fail_on=["x"])
    response = manager_client.post(
        "/sync/ingest",
        json={
            "idempotency_key": "rp",
            "operation": "op.fragile",
            "payload": {"op": "x"},
        },
    )
    assert response.status_code == 200
    pending = manager_client.get("/sync/pending")
    assert pending.status_code == 200
    assert pending.json() == {"pending_count": 1}


def test_failures_list_retry_and_resolve(
    manager_client: TestClient, operation_handlers: dict
) -> None:
    applied: list[str] = []
    fail_on = ["x"]
    operation_handlers["op.fragile"] = make_handler(applied, fail_on=fail_on)
    entry = ingest(manager_client, key="rf", operation="op.fragile", payload={"op": "x"})
    failures = manager_client.get("/sync/failures")
    assert failures.status_code == 200
    assert [f["id"] for f in failures.json()] == [entry["entry_id"]]
    fail_on.clear()
    retried = manager_client.post(f"/sync/failures/{entry['entry_id']}/retry")
    assert retried.status_code == 200
    assert retried.json()["status"] == "synced"
    assert applied == ["x"]
    assert manager_client.get("/sync/pending").json() == {"pending_count": 0}


def test_failures_resolve_endpoint(manager_client: TestClient, operation_handlers: dict) -> None:
    operation_handlers["op.fragile"] = make_handler([], fail_on=["x"])
    entry = ingest(manager_client, key="rr", operation="op.fragile", payload={"op": "x"})
    response = manager_client.post(f"/sync/failures/{entry['entry_id']}/resolve")
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert manager_client.get("/sync/pending").json() == {"pending_count": 0}


def test_failures_endpoint_not_found(manager_client: TestClient) -> None:
    assert manager_client.post("/sync/failures/999/retry").status_code == 404
    assert manager_client.post("/sync/failures/999/resolve").status_code == 404


def test_failures_manager_only(attendant_client: TestClient, operation_handlers: dict) -> None:
    operation_handlers["op.fragile"] = make_handler([], fail_on=["x"])
    entry = ingest(attendant_client, key="ra", operation="op.fragile", payload={"op": "x"})
    assert entry["status"] == "accepted"
    assert attendant_client.get("/sync/failures").status_code == 403
    assert attendant_client.post(f"/sync/failures/{entry['entry_id']}/retry").status_code == 403
    assert attendant_client.post(f"/sync/failures/{entry['entry_id']}/resolve").status_code == 403
