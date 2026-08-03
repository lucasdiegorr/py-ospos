"""Tests for the products and categories capability (HTTP + service layer)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.api.routers import categories as categories_router
from app.api.routers import products as products_router
from app.core.config import get_settings
from app.core.security import CurrentUser, Role
from app.db import Base
from app.main import app
from app.services import products as service

DB_URL = get_settings().database_url


def _db_up() -> bool:
    try:
        engine = create_engine(DB_URL, pool_pre_ping=True)
        with engine.connect():
            pass
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="requires a running PostgreSQL")


def _make_user(role: Role) -> CurrentUser:
    return CurrentUser(user_id=1, username="tester", role=role)


def _set_user(role: Role) -> None:
    """Override auth deps; manager-gated endpoints reject non-managers."""

    def manager_dep() -> CurrentUser:
        user = _make_user(role)
        if user.role not in (Role.MANAGER, Role.ADMIN):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    def attendant_dep() -> CurrentUser:
        return _make_user(role)

    app.dependency_overrides[products_router.manager_dep] = manager_dep
    app.dependency_overrides[products_router.attendant_dep] = attendant_dep
    app.dependency_overrides[categories_router.manager_dep] = manager_dep
    app.dependency_overrides[categories_router.attendant_dep] = attendant_dep


@pytest.fixture()
def db_env():
    engine = create_engine(DB_URL, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_env):
    with Session(db_env) as session:
        yield session
        session.rollback()


@pytest.fixture()
def client(db_env):
    app.dependency_overrides.clear()
    _set_user(Role.MANAGER)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_category(client: TestClient, name: str = "cerveja") -> dict:
    response = client.post("/categories", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def _create_product(
    client: TestClient,
    *,
    sku: str = "SKU-1",
    name: str = "Cerveja 600ml",
    category_id: int,
    unit_price_cents: int = 800,
    pack_quantity: int | None = None,
    pack_price_cents: int | None = None,
) -> dict:
    payload: dict = {
        "sku": sku,
        "name": name,
        "category_id": category_id,
        "unit_price_cents": unit_price_cents,
    }
    if pack_quantity is not None:
        payload["pack_quantity"] = pack_quantity
    if pack_price_cents is not None:
        payload["pack_price_cents"] = pack_price_cents
    response = client.post("/products", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_simple_product(client: TestClient) -> None:
    category = _create_category(client)
    product = _create_product(
        client, sku="AGUA-500", name="Água 500ml", category_id=category["id"], unit_price_cents=350
    )
    assert product["name"] == "Água 500ml"
    assert product["sku"] == "AGUA-500"
    assert product["unit_price_cents"] == 350
    assert product["category_id"] == category["id"]
    assert product["category_name"] == "cerveja"
    assert product["available_quantity"] == 0

    # searchable in the point of sale
    found = client.get("/products", params={"search": "água"}).json()
    assert [p["sku"] for p in found] == ["AGUA-500"]


def test_duplicate_sku_rejected(client: TestClient) -> None:
    category = _create_category(client)
    _create_product(client, sku="SKU-DUP", category_id=category["id"])
    response = client.post(
        "/products",
        json={
            "sku": "SKU-DUP",
            "name": "Another product",
            "category_id": category["id"],
            "unit_price_cents": 100,
        },
    )
    assert response.status_code == 409


def test_filter_by_category(client: TestClient) -> None:
    beer = _create_category(client, "cerveja")
    water = _create_category(client, "agua")
    _create_product(client, sku="CERVEJA-600", category_id=beer["id"])
    _create_product(client, sku="AGUA-500", name="Água 500ml", category_id=water["id"])

    result = client.get("/products", params={"category_id": beer["id"]}).json()
    assert [p["sku"] for p in result] == ["CERVEJA-600"]


def test_pack_definition(client: TestClient) -> None:
    category = _create_category(client)
    product = _create_product(
        client,
        sku="CERVEJA-12",
        category_id=category["id"],
        unit_price_cents=800,
        pack_quantity=12,
        pack_price_cents=8800,
    )
    assert product["pack_quantity"] == 12
    assert product["pack_price_cents"] == 8800
    # both the unit and the pack are offered by the point of sale
    assert product["unit_price_cents"] == 800


def test_pack_quantity_zero_rejected(client: TestClient) -> None:
    category = _create_category(client)
    response = client.post(
        "/products",
        json={
            "sku": "X",
            "name": "X",
            "category_id": category["id"],
            "unit_price_cents": 100,
            "pack_quantity": 0,
            "pack_price_cents": 1000,
        },
    )
    assert response.status_code == 422


def test_pack_quantity_fractional_rejected(client: TestClient) -> None:
    category = _create_category(client)
    response = client.post(
        "/products",
        json={
            "sku": "X",
            "name": "X",
            "category_id": category["id"],
            "unit_price_cents": 100,
            "pack_quantity": 2.5,
            "pack_price_cents": 1000,
        },
    )
    assert response.status_code == 422


def test_pack_requires_both_fields(client: TestClient) -> None:
    category = _create_category(client)
    response = client.post(
        "/products",
        json={
            "sku": "X",
            "name": "X",
            "category_id": category["id"],
            "unit_price_cents": 100,
            "pack_quantity": 12,
        },
    )
    assert response.status_code == 422


def test_search_by_name_and_sku(client: TestClient) -> None:
    category = _create_category(client)
    _create_product(client, sku="CERVEJA-600", category_id=category["id"], unit_price_cents=800)
    _create_product(client, sku="AGUA-500", name="Água 500ml", category_id=category["id"])

    by_name = client.get("/products", params={"search": "cerveja"}).json()
    assert [p["sku"] for p in by_name] == ["CERVEJA-600"]

    by_sku = client.get("/products", params={"search": "AGUA-500"}).json()
    assert [p["sku"] for p in by_sku] == ["AGUA-500"]


def test_list_shows_price_and_availability(client: TestClient, db_session: Session) -> None:
    from app.models.product import Product

    category = _create_category(client)
    product = _create_product(
        client,
        sku="CERVEJA-600",
        category_id=category["id"],
        unit_price_cents=800,
        pack_quantity=12,
        pack_price_cents=8800,
    )
    # The inventory capability owns stock; simulate its snapshot here.
    row = db_session.get(Product, product["id"])
    assert row is not None
    row.loose_units = 5
    row.packs = 3
    db_session.commit()

    result = client.get("/products").json()
    assert len(result) == 1
    assert result[0]["unit_price_cents"] == 800
    assert result[0]["pack_quantity"] == 12
    assert result[0]["available_quantity"] == 5 + 3 * 12


def test_edit_product_price(client: TestClient) -> None:
    category = _create_category(client)
    product = _create_product(client, sku="CERVEJA-600", category_id=category["id"])

    response = client.patch(f"/products/{product['id']}", json={"unit_price_cents": 900})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["unit_price_cents"] == 900

    # future sales use the updated price
    listing = client.get("/products", params={"search": "CERVEJA-600"}).json()
    assert listing[0]["unit_price_cents"] == 900


def test_edit_product_category_and_pack(client: TestClient) -> None:
    beer = _create_category(client, "cerveja")
    water = _create_category(client, "agua")
    product = _create_product(client, sku="CERVEJA-600", category_id=beer["id"])

    response = client.patch(
        f"/products/{product['id']}",
        json={"category_id": water["id"], "pack_quantity": 6, "pack_price_cents": 4400},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category_id"] == water["id"]
    assert body["category_name"] == "agua"
    assert body["pack_quantity"] == 6
    assert body["pack_price_cents"] == 4400


def test_attendant_can_search_but_not_manage(client: TestClient) -> None:
    category = _create_category(client)
    product = _create_product(client, sku="CERVEJA-600", category_id=category["id"])

    _set_user(Role.ATTENDANT)

    # search and listing are allowed for attendants
    assert client.get("/products").status_code == 200
    assert client.get(f"/products/{product['id']}").status_code == 200
    assert client.get("/categories").status_code == 200

    # management operations are blocked for attendants
    assert (
        client.post(
            "/products",
            json={
                "sku": "NOPE",
                "name": "Nope",
                "category_id": category["id"],
                "unit_price_cents": 100,
            },
        ).status_code
        == 403
    )
    assert client.post("/categories", json={"name": "nope"}).status_code == 403
    assert (
        client.patch(f"/products/{product['id']}", json={"unit_price_cents": 1}).status_code == 403
    )


def test_category_duplicate_rejected(client: TestClient) -> None:
    _create_category(client, "cerveja")
    response = client.post("/categories", json={"name": "cerveja"})
    assert response.status_code == 409


def test_category_rename(client: TestClient) -> None:
    category = _create_category(client, "cerveja")
    response = client.patch(f"/categories/{category['id']}", json={"name": "cervejas"})
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "cervejas"


def test_product_unknown_category(client: TestClient) -> None:
    response = client.post(
        "/products",
        json={"sku": "X", "name": "X", "category_id": 9999, "unit_price_cents": 100},
    )
    assert response.status_code == 404


def test_inactive_product_hidden_from_search(client: TestClient) -> None:
    category = _create_category(client)
    product = _create_product(client, sku="CERVEJA-600", category_id=category["id"])

    assert client.patch(f"/products/{product['id']}", json={"is_active": False}).status_code == 200
    assert client.get("/products").json() == []

    listing = client.get("/products", params={"include_inactive": True}).json()
    assert len(listing) == 1
    assert listing[0]["is_active"] is False


def test_expiration_lives_in_stock_batch_not_product() -> None:
    from app.models.inventory import StockBatch
    from app.models.product import Product

    assert not hasattr(Product, "expiration_date")
    assert hasattr(StockBatch, "expiration_date")


def test_service_duplicate_sku(db_session: Session) -> None:
    category = service.create_category(db_session, "cerveja")
    service.create_product(
        db_session, sku="SKU-1", name="Cerveja", category_id=category.id, unit_price_cents=800
    )
    with pytest.raises(HTTPException) as exc:
        service.create_product(
            db_session, sku="SKU-1", name="Cerveja 2", category_id=category.id, unit_price_cents=800
        )
    assert exc.value.status_code == 409


def test_service_pack_validation(db_session: Session) -> None:
    category = service.create_category(db_session, "cerveja")
    with pytest.raises(HTTPException) as exc:
        service.create_product(
            db_session,
            sku="SKU-1",
            name="Cerveja",
            category_id=category.id,
            unit_price_cents=800,
            pack_quantity=12,
        )
    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        service.create_product(
            db_session,
            sku="SKU-1",
            name="Cerveja",
            category_id=category.id,
            unit_price_cents=800,
            pack_quantity=0,
            pack_price_cents=8800,
        )
    assert exc.value.status_code == 422


def test_service_available_quantity(db_session: Session) -> None:
    category = service.create_category(db_session, "cerveja")
    product = service.create_product(
        db_session,
        sku="SKU-1",
        name="Cerveja",
        category_id=category.id,
        unit_price_cents=800,
        pack_quantity=12,
        pack_price_cents=8800,
    )
    product.loose_units = 5
    product.packs = 3
    db_session.commit()
    db_session.refresh(product)
    assert service.available_quantity(product) == 41
