"""Tests for the inventory capability (specs/inventory/spec.md)."""

from __future__ import annotations

import itertools
from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.core.security import CurrentUser, Role
from app.db import Base
from app.domain.idempotency import utcnow
from app.models.inventory import StockBatch
from app.models.product import Product
from app.services import inventory as service
from app.services import products as product_service
from app.services.inventory import (
    InsufficientStockError,
    InvalidQuantityError,
    UnknownProductError,
)
from app.services.products import available_quantity

_UNIQ = itertools.count(1)


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


def naive_utc(dt):
    return dt.replace(tzinfo=None)


def make_product(db: Session, *, pack_quantity: int | None = None, **overrides: object) -> Product:
    n = next(_UNIQ)
    category_id = product_service.create_category(db, f"Cat {n}").id
    return product_service.create_product(
        db,
        sku=f"SKU-{n}",
        name=f"Refrigerante {n}",
        category_id=category_id,
        unit_price_cents=500,
        pack_quantity=pack_quantity,
        pack_price_cents=5500 if pack_quantity else None,
        **overrides,
    )


def _client(db_session: Session, *, role: Role) -> Generator[TestClient, None, None]:
    from fastapi import HTTPException

    from app.api.routers.inventory import attendant_or_higher, manager_or_higher
    from app.db import get_db
    from app.main import app

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def gate(*allowed: Role):
        def dependency() -> CurrentUser:
            if role not in allowed:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return CurrentUser(user_id=7, username="tester", role=role)

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


# --- Stock query ------------------------------------------------------------


def test_stock_shown_in_base_units(db_session: Session) -> None:
    product = make_product(db_session, pack_quantity=12)
    service.record_entry(db_session, product_id=product.id, units=5)
    service.record_entry(db_session, product_id=product.id, packs=2)
    record = db_session.get(Product, product.id)
    assert record is not None
    assert record.loose_units == 5
    assert record.packs == 2
    assert available_quantity(record) == 29


# --- Manual stock entry ------------------------------------------------------


def test_manual_entry_adds_units_and_logs_movement(db_session: Session) -> None:
    product = make_product(db_session)
    service.record_entry(db_session, product_id=product.id, units=24, actor_id=3)
    record = db_session.get(Product, product.id)
    assert record is not None and record.loose_units == 24
    movements = service.list_movements(db_session, product.id)
    assert [(m.delta, m.reason, m.actor_id) for m in movements] == [(24, "entry", 3)]


def test_entry_with_expiration_creates_batch(db_session: Session) -> None:
    product = make_product(db_session)
    expires = naive_utc(utcnow() + timedelta(days=7))
    service.record_entry(db_session, product_id=product.id, units=24, expiration_date=expires)
    batch = db_session.scalar(select(StockBatch).where(StockBatch.product_id == product.id))
    assert batch is not None and batch.quantity == 24
    assert batch.expiration_date == expires


def test_entry_rejects_no_or_negative_quantity(db_session: Session) -> None:
    product = make_product(db_session)
    with pytest.raises(InvalidQuantityError):
        service.record_entry(db_session, product_id=product.id, units=0, packs=0)
    with pytest.raises(InvalidQuantityError):
        service.record_entry(db_session, product_id=product.id, units=-3)


# --- Stock outflow on sale ---------------------------------------------------


def test_selling_unit_decrements_by_one(db_session: Session) -> None:
    product = make_product(db_session)
    service.record_entry(db_session, product_id=product.id, units=5)
    service.consume_stock(db_session, product_id=product.id, quantity=1)
    record = db_session.get(Product, product.id)
    assert record is not None and record.loose_units == 4


def test_selling_pack_decrements_by_pack_quantity(db_session: Session) -> None:
    product = make_product(db_session, pack_quantity=12)
    service.record_entry(db_session, product_id=product.id, packs=2)
    service.consume_stock(db_session, product_id=product.id, quantity=12)
    record = db_session.get(Product, product.id)
    assert record is not None
    assert record.packs == 1
    assert record.loose_units == 0
    assert available_quantity(record) == 12


# --- Automatic pack break ----------------------------------------------------


def test_break_pack_to_sell_a_unit(db_session: Session) -> None:
    product = make_product(db_session, pack_quantity=12)
    service.record_entry(db_session, product_id=product.id, packs=10)
    service.consume_stock(db_session, product_id=product.id, quantity=1)
    record = db_session.get(Product, product.id)
    assert record is not None
    assert record.packs == 9
    assert record.loose_units == 11
    assert available_quantity(record) == 119
    reasons = [m.reason for m in service.list_movements(db_session, product.id)]
    assert "break" in reasons
    assert "sale" in reasons


def test_insufficient_total_stock_refuses(db_session: Session) -> None:
    product = make_product(db_session, pack_quantity=12)
    with pytest.raises(InsufficientStockError):
        service.consume_stock(db_session, product_id=product.id, quantity=13)
    record = db_session.get(Product, product.id)
    assert record is not None and record.packs == 0 and record.loose_units == 0


def test_sale_drains_oldest_dated_batches_first(db_session: Session) -> None:
    product = make_product(db_session)
    soon = naive_utc(utcnow() + timedelta(days=3))
    later = naive_utc(utcnow() + timedelta(days=10))
    service.record_entry(db_session, product_id=product.id, units=10, expiration_date=soon)
    service.record_entry(db_session, product_id=product.id, units=10, expiration_date=later)
    service.consume_stock(db_session, product_id=product.id, quantity=15)
    batches = list(
        db_session.scalars(select(StockBatch).where(StockBatch.product_id == product.id))
    )
    assert len(batches) == 1  # exhausted soon batch is dropped
    by_date = {b.expiration_date: b.quantity for b in batches}
    assert by_date[later] == 5


# --- Low-stock and expiration alerts -----------------------------------------


def test_low_stock_flags_at_or_below_threshold(db_session: Session) -> None:
    low = make_product(db_session, low_stock_threshold=20)
    service.record_entry(db_session, product_id=low.id, units=15)
    ok = make_product(db_session, low_stock_threshold=20)
    service.record_entry(db_session, product_id=ok.id, units=50)
    flagged = {p.sku for p in service.low_stock_products(db_session)}
    assert flagged == {low.sku}


def test_expiring_stock_within_window_and_expired(db_session: Session) -> None:
    product = make_product(db_session)
    service.record_entry(
        db_session, product_id=product.id, units=10, expiration_date=utcnow() + timedelta(days=5)
    )
    service.record_entry(
        db_session, product_id=product.id, units=8, expiration_date=utcnow() - timedelta(days=1)
    )
    service.record_entry(
        db_session, product_id=product.id, units=99, expiration_date=utcnow() + timedelta(days=60)
    )
    rows = service.expiring_stock(db_session, window_days=30)
    by_quantity = {r.quantity: r for r in rows}
    assert len(rows) == 2
    assert by_quantity[8].expired is True
    assert by_quantity[10].expired is False


# --- Stock adjustment --------------------------------------------------------


def test_adjustment_records_reason(db_session: Session) -> None:
    product = make_product(db_session)
    service.record_entry(db_session, product_id=product.id, units=10)
    service.adjust_stock(db_session, product_id=product.id, delta=-2, reason="breakage", actor_id=2)
    record = db_session.get(Product, product.id)
    assert record is not None and record.loose_units == 8
    movements = service.list_movements(db_session, product.id)
    assert [(m.reason, m.delta, m.actor_id) for m in movements] == [
        ("entry", 10, None),
        ("adjustment", -2, 2),
    ]


def test_adjustment_down_below_available_refused(db_session: Session) -> None:
    product = make_product(db_session)
    with pytest.raises(InsufficientStockError):
        service.adjust_stock(db_session, product_id=product.id, delta=-1, reason="oops")


def test_adjustment_requires_reason_and_nonzero_delta(db_session: Session) -> None:
    product = make_product(db_session)
    with pytest.raises(InvalidQuantityError):
        service.adjust_stock(db_session, product_id=product.id, delta=0, reason="x")
    with pytest.raises(InvalidQuantityError):
        service.adjust_stock(db_session, product_id=product.id, delta=1, reason="   ")


# --- Movement log / unknown product -----------------------------------------


def test_movement_log_chronological(db_session: Session) -> None:
    product = make_product(db_session)
    service.record_entry(db_session, product_id=product.id, units=10)
    service.record_entry(db_session, product_id=product.id, units=5)
    service.consume_stock(db_session, product_id=product.id, quantity=3)
    deltas = [m.delta for m in service.list_movements(db_session, product.id)]
    assert deltas == [10, 5, -3]


def test_unknown_product_raises(db_session: Session) -> None:
    with pytest.raises(UnknownProductError):
        service.record_entry(db_session, product_id=9999, units=1)


# --- Router ------------------------------------------------------------------


def test_entry_endpoint_manual_entry(manager_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    response = manager_client.post(f"/inventory/products/{product.id}/entry", json={"units": 24})
    assert response.status_code == 200
    body = response.json()
    assert body["available_quantity"] == 24
    assert body["loose_units"] == 24


def test_entry_endpoint_rejects_no_quantity(
    manager_client: TestClient, db_session: Session
) -> None:
    product = make_product(db_session)
    response = manager_client.post(
        f"/inventory/products/{product.id}/entry", json={"units": 0, "packs": 0}
    )
    assert response.status_code == 422


def test_entry_endpoint_manager_only(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    response = attendant_client.post(f"/inventory/products/{product.id}/entry", json={"units": 1})
    assert response.status_code == 403


def test_entry_endpoint_unknown_product_404(manager_client: TestClient) -> None:
    response = manager_client.post("/inventory/products/9999/entry", json={"units": 1})
    assert response.status_code == 404


def test_adjust_endpoint(manager_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    service.record_entry(db_session, product_id=product.id, units=10)
    response = manager_client.post(
        f"/inventory/products/{product.id}/adjust",
        json={"delta": -2, "reason": "breakage"},
    )
    assert response.status_code == 200
    assert response.json()["available_quantity"] == 8
    calls = manager_client.get(f"/inventory/products/{product.id}/movements").json()
    assert [m["reason"] for m in calls] == ["entry", "adjustment"]


def test_adjust_endpoint_insufficient_conflict(
    manager_client: TestClient, db_session: Session
) -> None:
    product = make_product(db_session)
    response = manager_client.post(
        f"/inventory/products/{product.id}/adjust", json={"delta": -5, "reason": "oops"}
    )
    assert response.status_code == 409


def test_movements_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    service.record_entry(db_session, product_id=product.id, units=10, actor_id=3)
    response = attendant_client.get(f"/inventory/products/{product.id}/movements")
    assert response.status_code == 200
    assert [m["reason"] for m in response.json()] == ["entry"]


def test_stock_endpoint_available_quantity(
    attendant_client: TestClient, db_session: Session
) -> None:
    product = make_product(db_session, pack_quantity=12)
    service.record_entry(db_session, product_id=product.id, units=5)
    service.record_entry(db_session, product_id=product.id, packs=2)
    response = attendant_client.get(f"/inventory/products/{product.id}/stock")
    assert response.status_code == 200
    assert response.json()["available_quantity"] == 29


def test_low_stock_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session, low_stock_threshold=10)
    service.record_entry(db_session, product_id=product.id, units=4)
    response = attendant_client.get("/inventory/low-stock")
    assert response.status_code == 200
    assert [p["id"] for p in response.json()] == [product.id]


def test_expiring_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    service.record_entry(
        db_session, product_id=product.id, units=12, expiration_date=utcnow() + timedelta(days=5)
    )
    response = attendant_client.get("/inventory/expiring", params={"window_days": 30})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["quantity"] == 12
    assert body[0]["expired"] is False
