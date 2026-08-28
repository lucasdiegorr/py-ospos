"""Tests for the deliveries capability (specs/deliveries/spec.md)."""

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
from app.models.delivery import Delivery, DeliveryStatusEvent
from app.services import deliveries as service
from app.services import products as product_service
from app.services import sales as sales_service

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


def make_product(db: Session):
    n = next(_UNIQ)
    category_id = product_service.create_category(db, f"Cat {n}").id
    return product_service.create_product(
        db,
        sku=f"SKU-{n}",
        name=f"Produto {n}",
        category_id=category_id,
        unit_price_cents=1000,
    )


def sale_with_delivery(db: Session, delivery: dict, *, status: str = "pending") -> Delivery:
    product = make_product(db)
    from app.services import inventory as inventory_service

    inventory_service.record_entry(db, product_id=product.id, units=10)
    delivery["status"] = status
    sale = sales_service.complete_sale(
        db,
        items=[{"product_id": product.id, "quantity": 1, "pack": False}],
        payments=[{"method": "cash", "amount_cents": 1000}],
        delivery=delivery,
    )
    assigned = db.scalar(select(Delivery).where(Delivery.sale_id == sale.id))
    assert assigned is not None
    return assigned


def _client(db_session: Session, *, role: Role) -> Generator[TestClient, None, None]:
    from fastapi import HTTPException

    from app.api.routers.deliveries import attendant_or_higher
    from app.db import get_db
    from app.main import app

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def gate():
        def dependency() -> CurrentUser:
            if role not in (Role.ATTENDANT, Role.MANAGER, Role.ADMIN):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return CurrentUser(user_id=7, username="tester", role=role)

        return dependency

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[attendant_or_higher] = gate()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def attendant_client(db_session: Session) -> Generator[TestClient, None, None]:
    yield from _client(db_session, role=Role.ATTENDANT)


# --- Registration on sale ----------------------------------------------------


def test_delivery_created_on_sale_is_pending(db_session: Session) -> None:
    delivery = sale_with_delivery(db_session, {"district": "Centro"})
    assert delivery.status == "pending"


def test_reference_only_address_accepted(db_session: Session) -> None:
    delivery = sale_with_delivery(db_session, {"reference": "casa amarela, perto da padaria"})
    assert delivery.reference == "casa amarela, perto da padaria"
    assert delivery.street is None
    assert delivery.district is None
    assert delivery.number is None


def test_full_address_stored(db_session: Session) -> None:
    delivery = sale_with_delivery(
        db_session,
        {
            "street": "Rua A",
            "number": "123",
            "district": "Centro",
            "complement": "Bloco 2",
            "reference": "proximo a praca",
        },
    )
    assert delivery.street == "Rua A"
    assert delivery.number == "123"
    assert delivery.district == "Centro"
    assert delivery.complement == "Bloco 2"
    assert delivery.reference == "proximo a praca"


# --- Status tracking ---------------------------------------------------------


def test_status_transitions_record_events(db_session: Session) -> None:
    delivery = sale_with_delivery(db_session, {})
    updated = service.update_delivery_status(
        db_session, delivery.id, status="in_transit", actor_id=3
    )
    assert updated.status == "in_transit"
    updated = service.update_delivery_status(
        db_session, delivery.id, status="delivered", actor_id=3
    )
    assert updated.status == "delivered"
    events = list(
        db_session.scalars(
            select(DeliveryStatusEvent)
            .where(DeliveryStatusEvent.delivery_id == delivery.id)
            .order_by(DeliveryStatusEvent.id)
        )
    )
    assert [event.status for event in events] == ["in_transit", "delivered"]
    assert events[0].actor_id == 3


def test_status_cannot_go_backwards(db_session: Session) -> None:
    delivery = sale_with_delivery(db_session, {})
    service.update_delivery_status(db_session, delivery.id, status="delivered", actor_id=3)
    with pytest.raises(service.DeliveryStatusError):
        service.update_delivery_status(db_session, delivery.id, status="pending", actor_id=3)


def test_status_must_be_valid_and_forward(db_session: Session) -> None:
    delivery = sale_with_delivery(db_session, {})
    with pytest.raises(service.DeliveryStatusError):
        service.update_delivery_status(db_session, delivery.id, status="lost", actor_id=3)
    service.update_delivery_status(db_session, delivery.id, status="in_transit", actor_id=3)
    with pytest.raises(service.DeliveryStatusError):
        service.update_delivery_status(db_session, delivery.id, status="in_transit", actor_id=3)
    with pytest.raises(service.DeliveryStatusError):
        service.update_delivery_status(db_session, delivery.id, status="pending", actor_id=3)


def test_unknown_delivery_raises(db_session: Session) -> None:
    with pytest.raises(service.DeliveryNotFound):
        service.update_delivery_status(db_session, 9999, status="in_transit", actor_id=3)


# --- Listing -----------------------------------------------------------------


def test_list_deliveries_filtered_by_status(db_session: Session) -> None:
    pending = sale_with_delivery(db_session, {"district": "Centro"})
    pending2 = sale_with_delivery(db_session, {"reference": "casa amarela"})
    delivered = sale_with_delivery(db_session, {"district": "Bairro Alto"}, status="delivered")

    only_pending = service.list_deliveries(db_session, status="pending")
    assert {d.id for d in only_pending} == {pending.id, pending2.id}

    only_delivered = service.list_deliveries(db_session, status="delivered")
    assert {d.id for d in only_delivered} == {delivered.id}


def test_list_deliveries_by_date_range(db_session: Session) -> None:
    delivery = sale_with_delivery(db_session, {})
    rows = service.list_deliveries(
        db_session,
        date_from=delivery.created_at - timedelta(days=1),
        date_to=delivery.created_at + timedelta(days=1),
    )
    assert [d.id for d in rows] == [delivery.id]
    rows = service.list_deliveries(
        db_session,
        date_from=delivery.created_at + timedelta(days=1),
    )
    assert rows == []


def test_list_returns_destination_and_sale_reference(db_session: Session) -> None:
    sale_with_delivery(db_session, {"street": "Rua A", "number": "123"})
    row = service.list_deliveries(db_session)[0]
    assert row.destination == "Rua A 123"
    assert row.sale_id is not None


# --- Router ------------------------------------------------------------------


def test_update_status_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    delivery = sale_with_delivery(db_session, {})
    response = attendant_client.patch(
        f"/deliveries/{delivery.id}/status", json={"status": "in_transit"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_transit"
    response = attendant_client.patch(
        f"/deliveries/{delivery.id}/status", json={"status": "delivered"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"


def test_update_status_endpoint_invalid_transition(
    attendant_client: TestClient, db_session: Session
) -> None:
    delivery = sale_with_delivery(db_session, {})
    response = attendant_client.patch(f"/deliveries/{delivery.id}/status", json={"status": "lost"})
    assert response.status_code == 422
    response = attendant_client.patch(
        f"/deliveries/{delivery.id}/status", json={"status": "delivered"}
    )
    assert response.status_code == 200
    response = attendant_client.patch(
        f"/deliveries/{delivery.id}/status", json={"status": "in_transit"}
    )
    assert response.status_code == 400


def test_update_status_endpoint_not_found(attendant_client: TestClient) -> None:
    response = attendant_client.patch("/deliveries/9999/status", json={"status": "in_transit"})
    assert response.status_code == 404


def test_list_deliveries_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    sale_with_delivery(db_session, {"district": "Centro"})
    sale_with_delivery(db_session, {"reference": "casa amarela"}, status="in_transit")
    response = attendant_client.get("/deliveries", params={"status": "pending"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["destination"] == "Centro"


def test_delivery_detail_endpoint(attendant_client: TestClient, db_session: Session) -> None:
    delivery = sale_with_delivery(db_session, {"district": "Centro"})
    response = attendant_client.get(f"/deliveries/{delivery.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["sale_id"] == delivery.sale_id
