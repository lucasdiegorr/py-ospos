from typing import Any
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.auth import get_current_user, get_db
from tests.conftest import MockDbSession, MockEmployee


class SaleMockDbSession(MockDbSession):
    def add(self, obj: Any) -> None:
        for attr in ("discount_amount", "discount_percent"):
            if hasattr(obj, attr) and getattr(obj, attr) is None:
                setattr(obj, attr, 0.0)
        super().add(obj)
        table_name = getattr(getattr(obj, "__table__", None), "name", None)
        if table_name == "sales":
            obj.__dict__["lines"] = []
            obj.__dict__["payments"] = []
        elif table_name == "sale_lines":
            sale_store = self._data.get("sales", {})
            parent = sale_store.get(getattr(obj, "sale_id", ""))
            if parent:
                parent.__dict__.setdefault("lines", []).append(obj)
        elif table_name == "payments":
            sale_store = self._data.get("sales", {})
            parent = sale_store.get(getattr(obj, "sale_id", ""))
            if parent:
                parent.__dict__.setdefault("payments", []).append(obj)

    async def delete(self, obj: Any) -> None:
        table_name = getattr(getattr(obj, "__table__", None), "name", None)
        if table_name == "sale_lines":
            sale_store = self._data.get("sales", {})
            parent = sale_store.get(getattr(obj, "sale_id", ""))
            if parent and hasattr(parent, "__dict__"):
                parent.__dict__.setdefault("lines", [])
                parent.__dict__["lines"] = [l for l in parent.__dict__["lines"] if l.id != obj.id]
        elif table_name == "payments":
            sale_store = self._data.get("sales", {})
            parent = sale_store.get(getattr(obj, "sale_id", ""))
            if parent and hasattr(parent, "__dict__"):
                parent.__dict__.setdefault("payments", [])
                parent.__dict__["payments"] = [p for p in parent.__dict__["payments"] if p.id != obj.id]
        await super().delete(obj)


@pytest.fixture
async def client() -> AsyncClient:
    async def mock_get_current_user():
        return MockEmployee()

    mock_session = SaleMockDbSession()

    async def mock_get_db():
        yield mock_session

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = mock_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _create_item(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {"name": "Widget", "unit_price": 10.00, "cost_price": 5.00, "quantity": 100}
    payload.update(overrides)
    resp = await client.post("/api/v1/items/", json=payload)
    assert resp.status_code == 201
    return resp.json()


async def _create_cart(client: AsyncClient) -> dict[str, Any]:
    resp = await client.post("/api/v1/sales/cart", json={})
    assert resp.status_code == 201
    return resp.json()


async def _add_item(client: AsyncClient, item_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {"item_id": item_id, "quantity": 1, "unit_price": 10.00}
    payload.update(overrides)
    resp = await client.post("/api/v1/sales/cart/items", json=payload)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.anyio
async def test_create_cart(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/sales/cart", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "open"
    assert data["employee_id"] == "test-user-id"
    assert data["subtotal"] == 0
    assert data["total"] == 0
    assert "id" in data
    assert "created_at" in data


@pytest.mark.anyio
async def test_get_current_cart(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/sales/cart")
    assert resp.status_code == 200
    assert resp.json() is None

    cart = await _create_cart(client)
    cart_id = cart["id"]

    resp = await client.get("/api/v1/sales/cart")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == cart_id
    assert data["status"] == "open"


@pytest.mark.anyio
async def test_add_item_to_cart(client: AsyncClient) -> None:
    item = await _create_item(client)
    item_id = item["id"]

    resp = await client.post(
        "/api/v1/sales/cart/items",
        json={"item_id": item_id, "quantity": 2, "unit_price": 15.00},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "open"
    assert len(data["lines"]) == 1
    line = data["lines"][0]
    assert line["item_id"] == item_id
    assert line["quantity"] == 2
    assert line["unit_price"] == 15.0
    assert line["line_total"] == 30.0
    assert "id" in line


@pytest.mark.anyio
async def test_update_cart_item(client: AsyncClient) -> None:
    item = await _create_item(client)
    cart = await _add_item(client, item["id"])
    line_id = cart["lines"][0]["id"]

    resp = await client.patch(
        "/api/v1/sales/cart/items",
        json={"line_id": line_id, "quantity": 5, "discount_percent": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["lines"]) == 1
    assert data["lines"][0]["quantity"] == 5
    assert data["lines"][0]["discount_percent"] == 10


@pytest.mark.anyio
async def test_remove_cart_item(client: AsyncClient) -> None:
    item = await _create_item(client)
    cart = await _add_item(client, item["id"])
    line_id = cart["lines"][0]["id"]

    resp = await client.delete(f"/api/v1/sales/cart/items/{line_id}")
    assert resp.status_code == 204

    cart_resp = await client.get("/api/v1/sales/cart")
    assert cart_resp.status_code == 200
    assert len(cart_resp.json()["lines"]) == 0


@pytest.mark.anyio
async def test_complete_sale(client: AsyncClient) -> None:
    item = await _create_item(client)
    await _create_cart(client)
    cart = await _add_item(client, item["id"])
    line_id = cart["lines"][0]["id"]

    await client.patch("/api/v1/sales/cart/items", json={"line_id": line_id, "quantity": 1})

    resp = await client.post(
        "/api/v1/sales/cart/complete",
        json={
            "payments": [{"payment_type": "cash", "amount": 10.00}],
            "comment": "Sold",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["comment"] == "Sold"
    assert data["completed_at"] is not None
    assert len(data["payments"]) == 1
    assert data["payments"][0]["payment_type"] == "cash"
    assert data["payments"][0]["amount"] == 10.0


@pytest.mark.anyio
async def test_complete_sale_insufficient_payment(client: AsyncClient) -> None:
    item = await _create_item(client)
    await _create_cart(client)
    cart = await _add_item(client, item["id"])
    line_id = cart["lines"][0]["id"]

    await client.patch("/api/v1/sales/cart/items", json={"line_id": line_id, "quantity": 1})

    resp = await client.post(
        "/api/v1/sales/cart/complete",
        json={"payments": [{"payment_type": "cash", "amount": 5.00}]},
    )
    assert resp.status_code == 400
    assert "Insufficient payment" in resp.json()["detail"]


@pytest.mark.anyio
async def test_suspend_cart(client: AsyncClient) -> None:
    await _create_cart(client)

    resp = await client.post("/api/v1/sales/cart/suspend")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "suspended"
    assert data["suspended_at"] is not None


@pytest.mark.anyio
async def test_list_suspended_sales(client: AsyncClient) -> None:
    await _create_cart(client)
    await client.post("/api/v1/sales/cart/suspend")
    await _create_cart(client)
    await client.post("/api/v1/sales/cart/suspend")

    resp = await client.get("/api/v1/sales/suspended")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    for sale in data:
        assert sale["status"] == "suspended"


@pytest.mark.anyio
async def test_recall_sale(client: AsyncClient) -> None:
    cart = await _create_cart(client)
    cart_id = cart["id"]
    await client.post("/api/v1/sales/cart/suspend")

    resp = await client.post(f"/api/v1/sales/suspended/{cart_id}/recall")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "open"
    assert data["id"] == cart_id
    assert data["suspended_at"] is None


@pytest.mark.anyio
async def test_void_sale(client: AsyncClient) -> None:
    cart = await _create_cart(client)
    cart_id = cart["id"]

    resp = await client.post(f"/api/v1/sales/{cart_id}/void")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "voided"


@pytest.mark.anyio
async def test_void_completed_sale(client: AsyncClient) -> None:
    item = await _create_item(client)
    await _create_cart(client)
    cart = await _add_item(client, item["id"])
    line_id = cart["lines"][0]["id"]
    await client.patch("/api/v1/sales/cart/items", json={"line_id": line_id, "quantity": 1})
    complete_resp = await client.post(
        "/api/v1/sales/cart/complete",
        json={"payments": [{"payment_type": "cash", "amount": 10.00}]},
    )
    assert complete_resp.status_code == 200
    sale_id = complete_resp.json()["id"]

    resp = await client.post(f"/api/v1/sales/{sale_id}/void")
    assert resp.status_code == 400
    assert "Cannot void completed sale" in resp.json()["detail"]
