"""Tests for the sales capability (specs/sales/spec.md)."""

from __future__ import annotations

import itertools
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.core.security import CurrentUser, Role
from app.db import Base
from app.models.delivery import Delivery
from app.models.sales import Sale
from app.schemas.customers import CustomerCreate, CustomerFiadoIn
from app.services import customers as customer_service
from app.services import inventory as inventory_service
from app.services import products as product_service
from app.services import sales as service
from app.services import sync as sync_service
from app.services.inventory import InsufficientStockError, UnknownProductError
from app.services.payments import FiadoLimitExceededError, PaymentError

_UNIQ = itertools.count(1)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    from app.services.payments import seed_default_payment_methods

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_default_payment_methods(session)
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def make_product(db: Session, *, pack_quantity: int | None = None, **overrides: object):
    n = next(_UNIQ)
    category_id = product_service.create_category(db, f"Cat {n}").id
    defaults: dict[str, object] = {
        "sku": f"SKU-{n}",
        "name": f"Cerveja {n}",
        "category_id": category_id,
        "unit_price_cents": 600,
        "pack_quantity": pack_quantity,
        "pack_price_cents": 6500 if pack_quantity else None,
    }
    defaults.update(overrides)
    return product_service.create_product(db, **defaults)


def make_customer(db: Session, *, credit_limit_cents: int | None = None):
    return customer_service.create_customer(
        db,
        CustomerCreate(
            name="Maria",
            fiado=(
                CustomerFiadoIn(credit_limit_cents=credit_limit_cents)
                if credit_limit_cents is not None
                else None
            ),
        ),
    )


def _client(db_session: Session, *, role: Role) -> Generator[TestClient, None, None]:
    from fastapi import HTTPException

    from app.api.routers.sales import attendant_or_higher, manager_or_higher
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
def attendant_client(db_session: Session) -> Generator[TestClient, None, None]:
    yield from _client(db_session, role=Role.ATTENDANT)


@pytest.fixture()
def manager_client(db_session: Session) -> Generator[TestClient, None, None]:
    yield from _client(db_session, role=Role.MANAGER)


def how_many(db: Session) -> int:
    return int(db.scalar(select(func.count(Sale.id))) or 0)


def sell(
    db: Session,
    items: list[dict],
    *,
    payments: list[dict],
    customer_id: int | None = None,
    **extra: object,
) -> Sale:
    return service.complete_sale(
        db,
        items=items,
        payments=payments,
        customer_id=customer_id,
        **extra,
    )


# --- Cart totals -------------------------------------------------------------


def test_unit_line_total_computed_server_side(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=500)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sale = sell(
        db_session,
        [{"product_id": product.id, "quantity": 2, "pack": False}],
        payments=[{"method": "cash", "amount_cents": 1000}],
    )
    assert sale.total_cents == 1000
    assert sale.items[0].unit_price_cents == 500
    assert sale.items[0].line_total_cents == 1000


def test_pack_line_uses_pack_price(db_session: Session) -> None:
    product = make_product(db_session, pack_quantity=12)
    inventory_service.record_entry(db_session, product_id=product.id, packs=5)
    sale = sell(
        db_session,
        [{"product_id": product.id, "quantity": 1, "pack": True}],
        payments=[{"method": "cash", "amount_cents": 6500}],
    )
    assert sale.total_cents == 6500
    item = sale.items[0]
    assert item.pack is True
    assert item.unit_price_cents == 6500
    assert item.line_total_cents == 6500


def test_cart_total_sums_lines(db_session: Session) -> None:
    unit = make_product(db_session, unit_price_cents=2000)
    pack = make_product(db_session, pack_quantity=12, pack_price_cents=3000)
    inventory_service.record_entry(db_session, product_id=unit.id, units=50)
    inventory_service.record_entry(db_session, product_id=pack.id, packs=10)
    sale = sell(
        db_session,
        [
            {"product_id": unit.id, "quantity": 1, "pack": False},
            {"product_id": pack.id, "quantity": 1, "pack": True},
        ],
        payments=[{"method": "cash", "amount_cents": 5000}],
    )
    assert sale.total_cents == 5000


# --- Completion and stock ----------------------------------------------------


def test_complete_sale_decrements_stock(db_session: Session) -> None:
    product = make_product(db_session, pack_quantity=12)
    inventory_service.record_entry(db_session, product_id=product.id, packs=5)
    sell(
        db_session,
        [{"product_id": product.id, "quantity": 1, "pack": True}],
        payments=[{"method": "cash", "amount_cents": 6500}],
    )
    record = db_session.get(type(product), product.id)
    from app.services.products import available_quantity

    assert record is not None and available_quantity(record) == 48


def test_partial_payment_blocked(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=1000)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    with pytest.raises(PaymentError):
        sell(
            db_session,
            [{"product_id": product.id, "quantity": 1, "pack": False}],
            payments=[{"method": "cash", "amount_cents": 500}],
        )
    db_session.rollback()
    assert how_many(db_session) == 0


def test_insufficient_stock_is_atomic(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=500)
    inventory_service.record_entry(db_session, product_id=product.id, units=5)
    with pytest.raises(InsufficientStockError):
        sell(
            db_session,
            [{"product_id": product.id, "quantity": 10, "pack": False}],
            payments=[{"method": "cash", "amount_cents": 5000}],
        )
    db_session.rollback()
    assert how_many(db_session) == 0
    record = db_session.get(type(product), product.id)
    assert record is not None and record.loose_units == 5


def test_unknown_product_blocks_sale(db_session: Session) -> None:
    with pytest.raises(UnknownProductError):
        sell(
            db_session,
            [{"product_id": 999, "quantity": 1, "pack": False}],
            payments=[{"method": "cash", "amount_cents": 100}],
        )


# --- Fiado -------------------------------------------------------------------


def test_fiado_within_limit_increases_balance(db_session: Session) -> None:
    customer = make_customer(db_session, credit_limit_cents=100000)
    product = make_product(db_session, unit_price_cents=10000)
    inventory_service.record_entry(db_session, product_id=product.id, units=20)
    sale = sell(
        db_session,
        [{"product_id": product.id, "quantity": 1, "pack": False}],
        payments=[{"method": "fiado", "amount_cents": 10000}],
        customer_id=customer.id,
    )
    assert sale.status == "completed"
    refreshed = customer_service.get_customer(db_session, customer.id)
    assert refreshed.outstanding_balance_cents == 10000


def test_fiado_requires_customer(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=1000)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    with pytest.raises(PaymentError):
        sell(
            db_session,
            [{"product_id": product.id, "quantity": 1, "pack": False}],
            payments=[{"method": "fiado", "amount_cents": 1000}],
        )


def test_fiado_over_limit_blocked(db_session: Session) -> None:
    customer = make_customer(db_session, credit_limit_cents=5000)
    product = make_product(db_session, unit_price_cents=10000)
    inventory_service.record_entry(db_session, product_id=product.id, units=20)
    with pytest.raises(FiadoLimitExceededError):
        sell(
            db_session,
            [{"product_id": product.id, "quantity": 1, "pack": False}],
            payments=[{"method": "fiado", "amount_cents": 10000}],
            customer_id=customer.id,
        )
    db_session.rollback()
    assert how_many(db_session) == 0


# --- Delivery -----------------------------------------------------------------


def test_optional_delivery_created(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=1000)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sale = sell(
        db_session,
        [{"product_id": product.id, "quantity": 1, "pack": False}],
        payments=[{"method": "cash", "amount_cents": 1000}],
        delivery={"district": "Centro", "reference": "Proximo ao mercado"},
    )
    delivery = db_session.scalar(select(Delivery).where(Delivery.sale_id == sale.id))
    assert delivery is not None
    assert delivery.status == "pending"
    assert delivery.district == "Centro"


# --- Offline / idempotency ---------------------------------------------------


def test_same_idempotency_key_returns_existing_sale(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=500)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    payload = {
        "items": [{"product_id": product.id, "quantity": 1, "pack": False}],
        "payments": [{"method": "cash", "amount_cents": 500}],
    }
    first = sell(
        db_session, payload["items"], payments=payload["payments"], idempotency_key="k-sale-1"
    )
    second = sell(
        db_session, payload["items"], payments=payload["payments"], idempotency_key="k-sale-1"
    )
    assert second.id == first.id
    assert how_many(db_session) == 1
    record = db_session.get(type(product), product.id)
    assert record is not None and record.loose_units == 9


def test_sync_handler_applies_sale_completed(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=500)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    payload = {
        "idempotency_key": "k-sync-1",
        "items": [{"product_id": product.id, "quantity": 2, "pack": False}],
        "payments": [{"method": "cash", "amount_cents": 1000}],
    }
    outcome, entry = sync_service.ingest_payload(
        db_session,
        idempotency_key="k-sync-1",
        operation="sale.completed",
        payload=payload,
    )
    assert outcome == "accepted"
    assert entry is not None and entry.status == "synced"
    assert how_many(db_session) == 1
    outcome, _ = sync_service.ingest_payload(
        db_session,
        idempotency_key="k-sync-1",
        operation="sale.completed",
        payload=payload,
    )
    assert outcome == "duplicate"
    assert how_many(db_session) == 1


# --- Cancel ------------------------------------------------------------------


def test_cancel_restores_stock_and_reverses_fiado(db_session: Session) -> None:
    customer = make_customer(db_session, credit_limit_cents=100000)
    product = make_product(db_session, pack_quantity=12)
    inventory_service.record_entry(db_session, product_id=product.id, packs=3)
    sale = sell(
        db_session,
        [{"product_id": product.id, "quantity": 1, "pack": True}],
        payments=[{"method": "fiado", "amount_cents": 6500}],
        customer_id=customer.id,
    )
    cancelled = service.cancel_sale(db_session, sale_id=sale.id, reason="client canceled")
    assert cancelled.status == "cancelled"
    assert cancelled.cancelled_reason == "client canceled"
    record = db_session.get(type(product), product.id)
    assert record is not None and record.packs == 3
    refreshed = customer_service.get_customer(db_session, customer.id)
    assert refreshed.outstanding_balance_cents == 0


def test_cancel_only_completed_and_requires_reason(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=500)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sale = sell(
        db_session,
        [{"product_id": product.id, "quantity": 1, "pack": False}],
        payments=[{"method": "cash", "amount_cents": 500}],
    )
    with pytest.raises(service.SaleError):
        service.cancel_sale(db_session, sale_id=sale.id, reason="   ")
    service.cancel_sale(db_session, sale_id=sale.id, reason="ok")
    with pytest.raises(service.SaleError):
        service.cancel_sale(db_session, sale_id=sale.id, reason="again")


# --- Search / detail / receipt ------------------------------------------------


def test_receipt_lines_include_items_payment_and_total(db_session: Session) -> None:
    product = make_product(db_session, unit_price_cents=1500)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sale = sell(
        db_session,
        [{"product_id": product.id, "quantity": 2, "pack": False}],
        payments=[{"method": "cash", "amount_cents": 3000}],
    )
    lines = service.receipt_lines(db_session, sale.id)
    text = "\n".join(lines)
    assert "Cerveja" in text
    assert "R$ 30.00" in text
    assert "cash" in text


def test_search_sales_by_customer(db_session: Session) -> None:
    customer = make_customer(db_session)
    other = make_customer(db_session, credit_limit_cents=1000)
    product = make_product(db_session, unit_price_cents=500)
    inventory_service.record_entry(db_session, product_id=product.id, units=20)
    sell(
        db_session,
        [{"product_id": product.id, "quantity": 1, "pack": False}],
        payments=[{"method": "cash", "amount_cents": 500}],
        customer_id=customer.id,
    )
    sell(
        db_session,
        [{"product_id": product.id, "quantity": 1, "pack": False}],
        payments=[{"method": "cash", "amount_cents": 500}],
        customer_id=other.id,
    )
    sales = service.search_sales(db_session, customer_id=customer.id)
    assert len(sales) == 1
    assert sales[0].customer_id == customer.id
    assert len(service.search_sales(db_session)) == 2


def test_get_sale_not_found(db_session: Session) -> None:
    with pytest.raises(service.SaleNotFound):
        service.get_sale(db_session, 999)


# --- Router ------------------------------------------------------------------


def test_complete_sale_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    response = attendant_client.post(
        "/sales",
        json={
            "items": [{"product_id": product.id, "quantity": 2, "pack": False}],
            "payments": [{"method": "cash", "amount_cents": 1200}],
        },
    )
    assert response.status_code == 201
    assert response.json()["total_cents"] == 1200
    assert response.json()["status"] == "completed"


def test_partial_payment_endpoint_400(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    response = attendant_client.post(
        "/sales",
        json={
            "items": [{"product_id": product.id, "quantity": 2, "pack": False}],
            "payments": [{"method": "cash", "amount_cents": 500}],
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Payments sum to 500 but the sale total is 1200"


def test_insufficient_stock_endpoint_409(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=1)
    response = attendant_client.post(
        "/sales",
        json={
            "items": [{"product_id": product.id, "quantity": 2, "pack": False}],
            "payments": [{"method": "cash", "amount_cents": 1200}],
        },
    )
    assert response.status_code == 409


def test_fiado_over_limit_endpoint_409(attendant_client: TestClient, db_session: Session) -> None:
    customer = make_customer(db_session, credit_limit_cents=100)
    product = make_product(db_session, unit_price_cents=1200)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    response = attendant_client.post(
        "/sales",
        json={
            "customer_id": customer.id,
            "items": [{"product_id": product.id, "quantity": 1, "pack": False}],
            "payments": [{"method": "fiado", "amount_cents": 1200}],
        },
    )
    assert response.status_code == 409


def test_cancel_endpoint_attendant_denied(
    attendant_client: TestClient, db_session: Session
) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sale_id = attendant_client.post(
        "/sales",
        json={
            "items": [{"product_id": product.id, "quantity": 1, "pack": False}],
            "payments": [{"method": "cash", "amount_cents": 600}],
        },
    ).json()["id"]
    response = attendant_client.post(f"/sales/{sale_id}/cancel", json={"reason": "x"})
    assert response.status_code == 403


def test_cancel_endpoint_manager_only(manager_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sale_id = manager_client.post(
        "/sales",
        json={
            "items": [{"product_id": product.id, "quantity": 1, "pack": False}],
            "payments": [{"method": "cash", "amount_cents": 600}],
        },
    ).json()["id"]
    response = manager_client.post(f"/sales/{sale_id}/cancel", json={"reason": "client canceled"})
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancelled_reason"] == "client canceled"


def test_sale_detail_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sale_id = attendant_client.post(
        "/sales",
        json={
            "items": [{"product_id": product.id, "quantity": 1, "pack": False}],
            "payments": [{"method": "cash", "amount_cents": 600}],
        },
    ).json()["id"]
    detail = attendant_client.get(f"/sales/{sale_id}")
    assert detail.status_code == 200
    assert len(detail.json()["items"]) == 1
    assert detail.json()["payments"][0]["method"] == "cash"


def test_sales_list_endpoint_by_customer(attendant_client: TestClient, db_session: Session) -> None:
    customer = make_customer(db_session)
    product = make_product(db_session, unit_price_cents=600)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    attendant_client.post(
        "/sales",
        json={
            "customer_id": customer.id,
            "items": [{"product_id": product.id, "quantity": 1, "pack": False}],
            "payments": [{"method": "cash", "amount_cents": 600}],
        },
    )
    response = attendant_client.get("/sales", params={"customer_id": customer.id})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_receipt_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sale_id = attendant_client.post(
        "/sales",
        json={
            "items": [{"product_id": product.id, "quantity": 1, "pack": False}],
            "payments": [{"method": "cash", "amount_cents": 600}],
        },
    ).json()["id"]
    body = attendant_client.get(f"/sales/{sale_id}/receipt")
    assert body.status_code == 200
    assert any("Cerveja" in line for line in body.json())


def test_complete_sale_validation(attendant_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    response = attendant_client.post(
        "/sales",
        json={"items": [{"product_id": product.id, "quantity": 0, "pack": False}], "payments": []},
    )
    assert response.status_code == 422
