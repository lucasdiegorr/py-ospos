"""Tests for the reporting capability (specs/reporting/spec.md)."""

from __future__ import annotations

import itertools
from collections.abc import Generator
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.core.security import CurrentUser, Role
from app.db import Base
from app.schemas.customers import CustomerCreate, CustomerFiadoIn
from app.services import customers as customer_service
from app.services import inventory as inventory_service
from app.services import products as product_service
from app.services import reporting as service
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


def make_product(db: Session, *, cost_price_cents: int | None = None, **overrides: object):
    n = next(_UNIQ)
    category_id = product_service.create_category(db, f"Cat {n}").id
    defaults: dict[str, object] = {
        "sku": f"SKU-{n}",
        "name": f"Produto {n}",
        "category_id": category_id,
        "unit_price_cents": 1000,
        "cost_price_cents": cost_price_cents,
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


def sell(db: Session, product, *, qty: int = 1, amount: int | None = None):
    if amount is None:
        amount = qty * product.unit_price_cents
    return sales_service.complete_sale(
        db,
        items=[{"product_id": product.id, "quantity": qty, "pack": False}],
        payments=[{"method": "cash", "amount_cents": amount}],
    )


def sell_on(db: Session, product, day: datetime) -> None:
    sale = sell(db, product)
    sale.created_at = day
    db.commit()


def sell_fiado_on(db: Session, customer_id: int, product_id: int, day: datetime) -> None:
    sale = sales_service.complete_sale(
        db,
        items=[{"product_id": product_id, "quantity": 1, "pack": False}],
        payments=[{"method": "fiado", "amount_cents": 1000}],
        customer_id=customer_id,
    )
    sale.created_at = day
    db.commit()


def _client(db_session: Session, *, role: Role) -> Generator[TestClient, None, None]:
    from fastapi import HTTPException

    from app.api.routers.reporting import manager_or_higher
    from app.db import get_db
    from app.main import app

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def gate():
        def dependency() -> CurrentUser:
            if role not in (Role.MANAGER, Role.ADMIN):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return CurrentUser(user_id=7, username="tester", role=role)

        return dependency

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[manager_or_higher] = gate()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def manager_client(db_session: Session) -> Generator[TestClient, None, None]:
    yield from _client(db_session, role=Role.MANAGER)


@pytest.fixture()
def attendant_client(db_session: Session) -> Generator[TestClient, None, None]:
    yield from _client(db_session, role=Role.ATTENDANT)


# --- Sales by period ---------------------------------------------------------


def test_sales_by_period_day(db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=50)
    sell_on(db_session, product, datetime(2026, 8, 10, 10, 0))
    sell_on(db_session, product, datetime(2026, 8, 10, 14, 0))
    sell_on(db_session, product, datetime(2026, 8, 11, 9, 0))
    rows = service.sales_by_period(
        db_session,
        period="day",
        date_from=datetime(2026, 8, 10),
        date_to=datetime(2026, 8, 11, 23, 59, 59),
    )
    by_day = {row["period"]: row for row in rows}
    day1 = by_day["2026-08-10"]
    assert day1["total_cents"] == 2000
    assert day1["sale_count"] == 2
    assert day1["avg_cents"] == 1000
    assert by_day["2026-08-11"]["sale_count"] == 1


def test_sales_by_period_month_buckets(db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=30)
    sell_on(db_session, product, datetime(2026, 7, 5))
    sell_on(db_session, product, datetime(2026, 8, 2))
    rows = service.sales_by_period(
        db_session,
        period="month",
        date_from=datetime(2026, 7, 1),
        date_to=datetime(2026, 8, 31, 23, 59, 59),
    )
    assert {row["period"] for row in rows} == {"2026-07", "2026-08"}


def test_sales_by_period_respects_range(db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=30)
    sell_on(db_session, product, datetime(2026, 7, 5))
    sell_on(db_session, product, datetime(2026, 8, 2))
    rows = service.sales_by_period(
        db_session,
        period="day",
        date_from=datetime(2026, 8, 1),
        date_to=datetime(2026, 8, 31, 23, 59, 59),
    )
    assert [row["period"] for row in rows] == ["2026-08-02"]


# --- Best sellers ------------------------------------------------------------


def test_best_sellers_ranked_by_quantity(db_session: Session) -> None:
    top = make_product(db_session)
    second = make_product(db_session, unit_price_cents=2000)
    inventory_service.record_entry(db_session, product_id=top.id, units=50)
    inventory_service.record_entry(db_session, product_id=second.id, units=50)
    sell(db_session, second, qty=1)
    sell(db_session, top, qty=3)
    rows = service.best_sellers(db_session, limit=10)
    assert rows[0]["product_id"] == top.id
    assert rows[0]["quantity"] == 3
    assert rows[0]["revenue_cents"] == 3000


# --- Critical stock ----------------------------------------------------------


def test_critical_stock_combines_low_and_expiring(db_session: Session) -> None:
    low = make_product(db_session, low_stock_threshold=10)
    inventory_service.record_entry(db_session, product_id=low.id, units=4)
    expiring = make_product(db_session)
    inventory_service.record_entry(
        db_session, product_id=expiring.id, units=12, expiration_date=datetime(2026, 9, 1)
    )
    report = service.critical_stock(db_session, window_days=30)
    assert [p["sku"] for p in report["low_stock"]] == [low.sku]
    assert [p["product_id"] for p in report["expiring"]] == [expiring.id]


# --- Open fiados -------------------------------------------------------------


def test_open_fiados_lists_balances_and_oldest_debt(db_session: Session) -> None:
    day1 = make_product(db_session)
    customer = make_customer(db_session, credit_limit_cents=50000)
    inventory_service.record_entry(db_session, product_id=day1.id, units=10)
    sell_fiado_on(db_session, customer.id, day1.id, datetime(2026, 7, 20))
    sell_fiado_on(db_session, customer.id, day1.id, datetime(2026, 7, 25))
    zero = make_customer(db_session)
    rows = {r["customer_id"]: r for r in service.open_fiados(db_session)}
    assert customer.id in rows
    assert rows[customer.id]["outstanding_balance_cents"] == 2000
    assert rows[customer.id]["oldest_debt_at"] == datetime(2026, 7, 20)
    assert zero.id not in rows


# --- Cash flow ---------------------------------------------------------------


def test_cash_flow_daily_in_out_net(db_session: Session) -> None:
    from app.services import cash_register
    from app.services.cash_register import Role as _Role  # noqa: F401  (uses Role below)

    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sell(db_session, product, amount=1000)
    shift = cash_register.open_shift(db_session, attendant_id=3, float_cents=0)
    cash_register.record_movement(
        db_session, shift_id=shift.id, type="supply", amount_cents=5000, reason="troco", actor_id=3
    )
    cash_register.record_movement(
        db_session, shift_id=shift.id, type="bleed", amount_cents=3000, reason="despesa", actor_id=3
    )
    rows = service.cash_flow(db_session, date_from=datetime.now() - timedelta(days=1))
    bucket = rows[0]
    assert bucket["sales_cents"] == 1000
    assert bucket["supplies_cents"] == 5000
    assert bucket["bleeds_cents"] == 3000
    assert bucket["in_cents"] == 6000
    assert bucket["out_cents"] == 3000
    assert bucket["net_cents"] == 3000


# --- Margin ------------------------------------------------------------------


def test_margin_with_and_without_cost(db_session: Session) -> None:
    with_cost = make_product(db_session, unit_price_cents=1000, cost_price_cents=700)
    no_cost = make_product(db_session, unit_price_cents=2000, cost_price_cents=None)
    inventory_service.record_entry(db_session, product_id=with_cost.id, units=10)
    inventory_service.record_entry(db_session, product_id=no_cost.id, units=10)
    sell(db_session, with_cost, qty=2)
    sell(db_session, no_cost)
    rows = {r["product_id"]: r for r in service.margin_by_product(db_session)}
    assert rows[with_cost.id]["revenue_cents"] == 2000
    assert rows[with_cost.id]["margin_cents"] == 600
    assert rows[no_cost.id]["revenue_cents"] == 2000
    assert rows[no_cost.id]["margin_cents"] is None


# --- Pending sync ------------------------------------------------------------


def test_pending_sync_count_from_sync_capability(db_session: Session) -> None:
    assert service.pending_sync_count(db_session) == 0


# --- Router ------------------------------------------------------------------


def test_reports_are_attendant_denied(attendant_client: TestClient) -> None:
    assert attendant_client.get("/reports/sales-by-period").status_code == 403
    assert attendant_client.get("/reports/best-sellers").status_code == 403
    assert attendant_client.get("/reports/critical-stock").status_code == 403
    assert attendant_client.get("/reports/open-fiados").status_code == 403
    assert attendant_client.get("/reports/cash-flow").status_code == 403
    assert attendant_client.get("/reports/margin").status_code == 403
    assert attendant_client.get("/reports/pending-sync").status_code == 403


def test_reports_open_to_manager(manager_client: TestClient) -> None:
    assert manager_client.get("/reports/sales-by-period").status_code == 200
    assert manager_client.get("/reports/open-fiados").status_code == 200
    assert manager_client.get("/reports/critical-stock").status_code == 200


def test_sales_by_period_endpoint(manager_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sell(db_session, product)
    response = manager_client.get("/reports/sales-by-period", params={"period": "day"})
    assert response.status_code == 200
    assert response.json()[0]["total_cents"] == 1000


def test_best_sellers_endpoint(manager_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sell(db_session, product)
    response = manager_client.get("/reports/best-sellers")
    assert response.status_code == 200
    assert response.json()[0]["product_id"] == product.id


def test_critical_stock_endpoint(manager_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session, low_stock_threshold=5)
    inventory_service.record_entry(db_session, product_id=product.id, units=2)
    response = manager_client.get("/reports/critical-stock")
    assert response.status_code == 200
    assert response.json()["low_stock"][0]["sku"] == product.sku


def test_open_fiados_endpoint(manager_client: TestClient, db_session: Session) -> None:
    customer = make_customer(db_session, credit_limit_cents=10000)
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sales_service.complete_sale(
        db_session,
        items=[{"product_id": product.id, "quantity": 1, "pack": False}],
        payments=[{"method": "fiado", "amount_cents": 1000}],
        customer_id=customer.id,
    )
    response = manager_client.get("/reports/open-fiados")
    assert response.status_code == 200
    assert response.json()[0]["customer_id"] == customer.id


def test_cash_flow_endpoint(manager_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sell(db_session, product)
    response = manager_client.get("/reports/cash-flow")
    assert response.status_code == 200
    assert response.json()[0]["sales_cents"] == 1000


def test_margin_endpoint(manager_client: TestClient, db_session: Session) -> None:
    product = make_product(db_session, cost_price_cents=700)
    inventory_service.record_entry(db_session, product_id=product.id, units=10)
    sell(db_session, product)
    response = manager_client.get("/reports/margin")
    assert response.status_code == 200
    assert response.json()[0]["margin_cents"] == 300


def test_pending_sync_endpoint(manager_client: TestClient) -> None:
    response = manager_client.get("/reports/pending-sync")
    assert response.status_code == 200
    assert response.json() == {"pending_sync_count": 0}
