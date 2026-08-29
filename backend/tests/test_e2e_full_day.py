"""End-to-end test of a full day of operations (task 13.7) using a fresh SQLite DB.

This test avoids interfering with the Postgres test suite by using an in‑memory
SQLite database. It seeds the catalog via the service layer, then drives the
real HTTP API (with JWT auth) through a full day: open shift, sell online
(cash + fiado), sell offline (via /sync/ingest), do supply/bleed, close shift,
and verify reports.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.core.security import Role
from app.db import Base
from app.schemas.customers import CustomerCreate
from app.services import customers as customer_service
from app.services import inventory as inventory_service
from app.services import products as product_service
from app.services import users as user_service
from app.services.payments import seed_default_payment_methods


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
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


def _login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_full_day_integration(db_session: Session) -> None:
    # --- catalog and people setup --------------------------------------------
    attendant = user_service.create_user(
        db_session,
        name="Atendente",
        username="at",
        password="secret123",
        role=Role.ATTENDANT,
    )
    manager = user_service.create_user(
        db_session,
        name="Gerente",
        username="mgr",
        password="secret123",
        role=Role.MANAGER,
    )
    category = product_service.create_category(db_session, "Bebidas")
    produto = product_service.create_product(
        db_session,
        sku="SKU-1",
        name="Cerveja 600ml",
        category_id=category.id,
        unit_price_cents=500,
        pack_quantity=12,
        pack_price_cents=5500,
        low_stock_threshold=10,
    )
    inventory_service.record_entry(db_session, product_id=produto.id, units=100)
    customer = customer_service.create_customer(
        db_session, CustomerCreate(name="Maria", fiado=None)
    )
    db_session.flush()  # make ids visible, but keep transaction open for rollback

    # --- HTTP test client bound to this session -------------------------------
    from app import main
    from app.db import get_db

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as client:
        attendant_headers = _login(client, attendant.username)
        manager_headers = _login(client, manager.username)

        # --- open the shift ---------------------------------------------------
        shift = client.post("/shifts", json={"float_cents": 10000}, headers=attendant_headers)
        assert shift.status_code == 201, shift.text
        shift_id = shift.json()["id"]

        # --- sell online: cash and fiado --------------------------------------
        cash = client.post(
            "/sales",
            json={
                "items": [{"product_id": produto.id, "quantity": 2, "pack": False}],
                "payments": [{"method": "cash", "amount_cents": 1000}],
            },
            headers=attendant_headers,
        )
        assert cash.status_code == 201, cash.text
        fiado = client.post(
            "/sales",
            json={
                "customer_id": customer.id,
                "items": [{"product_id": produto.id, "quantity": 1, "pack": False}],
                "payments": [{"method": "fiado", "amount_cents": 500}],
            },
            headers=attendant_headers,
        )
        assert fiado.status_code == 201, fiado.text

        # --- sell offline: queued and later pushed via sync ingestion ---------
        offline_payload = {
            "idempotency_key": "e2e-offline-1",
            "items": [{"product_id": produto.id, "quantity": 1, "pack": True}],
            "payments": [{"method": "cash", "amount_cents": 5500}],
        }
        synced = client.post(
            "/sync/ingest",
            json={
                "idempotency_key": "e2e-offline-1",
                "operation": "sale.completed",
                "payload": offline_payload,
            },
            headers=attendant_headers,
        )
        assert synced.status_code == 200 and synced.json()["status"] == "accepted", synced.text
        duplicate = client.post(
            "/sync/ingest",
            json={
                "idempotency_key": "e2e-offline-1",
                "operation": "sale.completed",
                "payload": offline_payload,
            },
            headers=attendant_headers,
        )
        assert duplicate.json()["status"] == "duplicate"

        # --- supply and bleed ------------------------------------------------
        supply = client.post(
            f"/shifts/{shift_id}/movements",
            json={"type": "supply", "amount_cents": 2000, "reason": "fundo de troco"},
            headers=attendant_headers,
        )
        assert supply.status_code == 200, supply.text
        bleed = client.post(
            f"/shifts/{shift_id}/movements",
            json={"type": "bleed", "amount_cents": 500, "reason": "despesa"},
            headers=attendant_headers,
        )
        assert bleed.status_code == 200, bleed.text

        # --- shift summary: expected = float + cash sales + supplies - bleeds --
        summary = client.get(f"/shifts/{shift_id}", headers=attendant_headers).json()
        assert summary["payment_totals"]["cash"] == 1000
        assert summary["payment_totals"]["fiado"] == 500
        assert summary["supplies_cents"] == 2000
        assert summary["bleeds_cents"] == 500
        assert summary["expected_cents"] == 10000 + 1000 + 2000 - 500  # = 12500

        # --- close with balanced count ---------------------------------------
        closed = client.post(
            f"/shifts/{shift_id}/close",
            json={"counted_cents": 12500},
            headers=attendant_headers,
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["difference_cents"] == 0

        # --- reports reflect the whole day (both online and offline sales) ----
        period = client.get("/reports/sales-by-period", headers=manager_headers)
        assert period.status_code == 200, period.text
        total_revenue = sum(row["total_cents"] for row in period.json())
        assert total_revenue == 1000 + 500 + 5500  # cash + fiado + offline pack

        best = client.get("/reports/best-sellers", headers=manager_headers).json()
        assert best[0]["product_id"] == produto.id
        assert best[0]["quantity"] == 4  # 2 units + 1 unit + 1 pack
        assert best[0]["revenue_cents"] == 7000

        fiados = client.get("/reports/open-fiados", headers=manager_headers).json()
        assert {row["customer_id"] for row in fiados} == {customer.id}
        assert fiados[0]["outstanding_balance_cents"] == 500

        pending = client.get("/reports/pending-sync", headers=manager_headers).json()
        assert pending == {"pending_sync_count": 0}

        # stock after: 100 - 2 (cash) - 1 (fiado) - 12 (offline pack) = 85
        stock = client.get(f"/inventory/products/{produto.id}/stock", headers=attendant_headers)
        assert stock.status_code == 200
        assert stock.json()["available_quantity"] == 85

        # --- attendant cannot open reports (role access) ----------------------
        assert client.get("/reports/sales-by-period", headers=attendant_headers).status_code == 403

        # the attendant recorded on the shift is the one who logged in
        assert closed.json()["attendant_id"] == attendant.id

    main.app.dependency_overrides.clear()
