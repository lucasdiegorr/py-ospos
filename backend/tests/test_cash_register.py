"""Tests for the cash-register capability (specs/cash-register/spec.md)."""

from __future__ import annotations

import itertools
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.core.security import CurrentUser, Role
from app.db import Base
from app.services import cash_register as service
from app.services import inventory as inventory_service
from app.services import products as product_service
from app.services import sales as sales_service
from app.services.cash_register import (
    InvalidMovementError,
    ShiftAlreadyOpenError,
    ShiftClosedError,
    ShiftError,
    ShiftNotFound,
)

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


def make_product(db: Session, *, unit_price_cents: int = 1000):
    n = next(_UNIQ)
    category_id = product_service.create_category(db, f"Cat {n}").id
    return product_service.create_product(
        db,
        sku=f"SKU-{n}",
        name=f"Produto {n}",
        category_id=category_id,
        unit_price_cents=unit_price_cents,
    )


def make_cash_sale(db: Session, *, shift_id: int, amount_cents: int) -> None:
    product = make_product(db, unit_price_cents=amount_cents)
    inventory_service.record_entry(db, product_id=product.id, units=10)
    sales_service.complete_sale(
        db,
        items=[{"product_id": product.id, "quantity": 1, "pack": False}],
        payments=[{"method": "cash", "amount_cents": amount_cents}],
        shift_id=shift_id,
    )


def _client(db_session: Session, *, role: Role) -> Generator[TestClient, None, None]:
    from fastapi import HTTPException

    from app.api.routers.cash_register import attendant_or_higher
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


# --- Open shift --------------------------------------------------------------


def test_open_shift_records_float(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=10000)
    assert shift.status == "open"
    assert shift.attendant_id == 3
    assert shift.float_cents == 10000
    assert service.active_shift(db_session).id == shift.id


def test_cannot_open_second_shift_while_active(db_session: Session) -> None:
    service.open_shift(db_session, attendant_id=3, float_cents=0)
    with pytest.raises(ShiftAlreadyOpenError):
        service.open_shift(db_session, attendant_id=4, float_cents=0)


def test_no_active_shift_when_none_open(db_session: Session) -> None:
    assert service.active_shift(db_session) is None


def test_requires_actor_for_open(db_session: Session) -> None:
    with pytest.raises(ShiftError):
        service.open_shift(db_session, attendant_id=None, float_cents=0)


# --- Movements ---------------------------------------------------------------


def test_supply_and_bleed_are_logged(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=10000)
    supply = service.record_movement(
        db_session,
        shift_id=shift.id,
        type="supply",
        amount_cents=5000,
        reason="fundo de troco",
        actor_id=3,
    )
    bleed = service.record_movement(
        db_session,
        shift_id=shift.id,
        type="bleed",
        amount_cents=8000,
        reason="despesa",
        actor_id=3,
    )
    assert (supply.type, supply.amount_cents) == ("supply", 5000)
    assert (bleed.type, bleed.amount_cents) == ("bleed", 8000)


def test_movement_requires_open_shift(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=0)
    service.close_shift(
        db_session, shift_id=shift.id, counted_cents=0, actor_id=3, actor_role=Role.ATTENDANT
    )
    with pytest.raises(ShiftClosedError):
        service.record_movement(
            db_session, shift_id=shift.id, type="supply", amount_cents=100, reason="x", actor_id=3
        )


def test_movement_validates_amount_and_reason(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=0)
    with pytest.raises(InvalidMovementError):
        service.record_movement(
            db_session, shift_id=shift.id, type="supply", amount_cents=0, reason="x", actor_id=3
        )
    with pytest.raises(InvalidMovementError):
        service.record_movement(
            db_session, shift_id=shift.id, type="supply", amount_cents=100, reason="  ", actor_id=3
        )
    with pytest.raises(InvalidMovementError):
        service.record_movement(
            db_session, shift_id=shift.id, type="loan", amount_cents=100, reason="x", actor_id=3
        )


def test_unknown_shift_raises(db_session: Session) -> None:
    with pytest.raises(ShiftNotFound):
        service.get_shift(db_session, 9999)


# --- Expected cash -----------------------------------------------------------


def test_expected_cash_matches_spec_example(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=10000)
    make_cash_sale(db_session, shift_id=shift.id, amount_cents=30000)
    service.record_movement(
        db_session, shift_id=shift.id, type="supply", amount_cents=5000, reason="troco", actor_id=3
    )
    service.record_movement(
        db_session, shift_id=shift.id, type="bleed", amount_cents=8000, reason="despesa", actor_id=3
    )
    assert service.expected_cash(db_session, shift.id) == 37000


# --- Close -------------------------------------------------------------------


def test_balanced_close(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=10000)
    make_cash_sale(db_session, shift_id=shift.id, amount_cents=10000)
    closed = service.close_shift(
        db_session, shift_id=shift.id, counted_cents=20000, actor_id=3, actor_role=Role.ATTENDANT
    )
    assert closed.status == "closed"
    assert closed.counted_cents == 20000
    summary = service.shift_summary(db_session, shift.id)
    assert summary["expected_cents"] == 20000
    assert summary["difference_cents"] == 0


def test_close_records_difference(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=10000)
    make_cash_sale(db_session, shift_id=shift.id, amount_cents=30000)
    service.record_movement(
        db_session, shift_id=shift.id, type="bleed", amount_cents=5000, reason="x", actor_id=3
    )
    closed = service.close_shift(
        db_session, shift_id=shift.id, counted_cents=34500, actor_id=3, actor_role=Role.ATTENDANT
    )
    assert closed.status == "closed"
    assert closed.counted_cents == 34500
    summary = service.shift_summary(db_session, shift.id)
    assert summary["expected_cents"] == 35000
    assert summary["difference_cents"] == -500


def test_close_only_by_owner_or_manager(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=0)
    with pytest.raises(ShiftError):
        service.close_shift(
            db_session, shift_id=shift.id, counted_cents=0, actor_id=9, actor_role=Role.ATTENDANT
        )
    closed = service.close_shift(
        db_session, shift_id=shift.id, counted_cents=0, actor_id=9, actor_role=Role.MANAGER
    )
    assert closed.status == "closed"


def test_after_close_no_active_shift(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=0)
    service.close_shift(
        db_session, shift_id=shift.id, counted_cents=0, actor_id=3, actor_role=Role.ATTENDANT
    )
    assert service.active_shift(db_session) is None
    with pytest.raises(ShiftClosedError):
        service.close_shift(
            db_session, shift_id=shift.id, counted_cents=0, actor_id=3, actor_role=Role.ATTENDANT
        )


# --- Summary -----------------------------------------------------------------


def test_shift_summary_includes_per_method_totals(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=10000)
    make_cash_sale(db_session, shift_id=shift.id, amount_cents=30000)
    service.record_movement(
        db_session, shift_id=shift.id, type="supply", amount_cents=5000, reason="troco", actor_id=3
    )
    service.record_movement(
        db_session, shift_id=shift.id, type="bleed", amount_cents=8000, reason="despesa", actor_id=3
    )
    summary = service.shift_summary(db_session, shift.id)
    assert summary["float_cents"] == 10000
    assert summary["payment_totals"] == {"cash": 30000}
    assert summary["supplies_cents"] == 5000
    assert summary["bleeds_cents"] == 8000
    assert summary["expected_cents"] == 37000
    assert summary["counted_cents"] is None
    assert summary["difference_cents"] is None


def test_list_shifts_filtered_by_status(db_session: Session) -> None:
    shift = service.open_shift(db_session, attendant_id=3, float_cents=0)
    assert [s.id for s in service.list_shifts(db_session, status="open")] == [shift.id]
    service.close_shift(
        db_session, shift_id=shift.id, counted_cents=0, actor_id=3, actor_role=Role.ATTENDANT
    )
    assert service.list_shifts(db_session, status="open") == []
    assert [s.id for s in service.list_shifts(db_session, status="closed")] == [shift.id]


# --- Router ------------------------------------------------------------------


def test_open_shift_endpoint(attendant_client: TestClient) -> None:
    response = attendant_client.post("/shifts", json={"float_cents": 10000})
    assert response.status_code == 201
    assert response.json()["status"] == "open"
    assert response.json()["float_cents"] == 10000


def test_open_shift_endpoint_second_refused(attendant_client: TestClient) -> None:
    assert attendant_client.post("/shifts", json={"float_cents": 0}).status_code == 201
    assert attendant_client.post("/shifts", json={"float_cents": 0}).status_code == 409


def test_current_shift_endpoint(attendant_client: TestClient) -> None:
    assert attendant_client.get("/shifts/current").status_code == 404
    shift_id = attendant_client.post("/shifts", json={"float_cents": 5000}).json()["id"]
    response = attendant_client.get("/shifts/current")
    assert response.status_code == 200
    assert response.json()["id"] == shift_id


def test_movement_endpoint(attendant_client: TestClient) -> None:
    shift_id = attendant_client.post("/shifts", json={"float_cents": 0}).json()["id"]
    response = attendant_client.post(
        f"/shifts/{shift_id}/movements",
        json={"type": "supply", "amount_cents": 5000, "reason": "troco"},
    )
    assert response.status_code == 200
    assert response.json()["type"] == "supply"


def test_close_endpoint(attendant_client: TestClient) -> None:
    shift_id = attendant_client.post("/shifts", json={"float_cents": 10000}).json()["id"]
    response = attendant_client.post(f"/shifts/{shift_id}/close", json={"counted_cents": 10000})
    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    assert response.json()["difference_cents"] == 0


def test_shift_summary_endpoint(attendant_client: TestClient) -> None:
    shift_id = attendant_client.post("/shifts", json={"float_cents": 10000}).json()["id"]
    response = attendant_client.get(f"/shifts/{shift_id}")
    assert response.status_code == 200
    assert response.json()["expected_cents"] == 10000
