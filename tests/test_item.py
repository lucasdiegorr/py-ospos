import pytest
from httpx import AsyncClient

from app.core.auth import get_current_user
from app.main import app


class _NonAdminEmployee:
    id = "non-admin-id"
    username = "nonadmin"
    first_name = "Non"
    last_name = "Admin"
    email = "nonadmin@example.com"
    is_active = True


@pytest.mark.anyio
async def test_create_category(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/items/categories",
        json={"name": "Beverages", "description": "Drinks and liquids"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Beverages"
    assert data["description"] == "Drinks and liquids"
    assert "id" in data


@pytest.mark.anyio
async def test_list_categories(client: AsyncClient) -> None:
    await client.post("/api/v1/items/categories", json={"name": "Snacks"})
    await client.post("/api/v1/items/categories", json={"name": "Dairy"})

    response = await client.get("/api/v1/items/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.anyio
async def test_create_item(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/items/",
        json={
            "name": "Test Item",
            "description": "A test item",
            "sku": "TST-001",
            "cost_price": 10.00,
            "unit_price": 19.99,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["sku"] == "TST-001"
    assert data["cost_price"] == 10.00
    assert data["unit_price"] == 19.99
    assert "id" in data


@pytest.mark.anyio
async def test_list_items(client: AsyncClient) -> None:
    await client.post("/api/v1/items/", json={"name": "Item A"})
    await client.post("/api/v1/items/", json={"name": "Item B"})

    response = await client.get("/api/v1/items/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.anyio
async def test_list_items_with_filters(client: AsyncClient) -> None:
    cat_resp = await client.post(
        "/api/v1/items/categories", json={"name": "FilterCat"}
    )
    cat_id = cat_resp.json()["id"]

    await client.post(
        "/api/v1/items/",
        json={"name": "Service Item 1", "category_id": cat_id, "is_service": True},
    )
    await client.post(
        "/api/v1/items/",
        json={"name": "Product Item 1", "category_id": cat_id, "is_service": False},
    )

    response = await client.get(f"/api/v1/items/?category_id={cat_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    response = await client.get(
        f"/api/v1/items/?category_id={cat_id}&is_service=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Service Item 1"


@pytest.mark.anyio
async def test_get_item(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/items/", json={"name": "Get Item Test"}
    )
    item_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == "Get Item Test"


@pytest.mark.anyio
async def test_get_item_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/items/non-existent-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_item(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/items/",
        json={"name": "Before Update", "unit_price": 10.00},
    )
    item_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/items/{item_id}",
        json={"name": "After Update", "unit_price": 15.00},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "After Update"
    assert data["unit_price"] == 15.00


@pytest.mark.anyio
async def test_delete_item(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/items/", json={"name": "Delete Me"}
    )
    item_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/items/{item_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_item_forbidden(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/items/", json={"name": "No Delete"}
    )
    item_id = create_resp.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: _NonAdminEmployee()

    response = await client.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 403


@pytest.mark.anyio
async def test_add_item_attribute(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/items/", json={"name": "Attribute Item"}
    )
    item_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/items/{item_id}/attributes",
        json={"attribute_name": "Color", "attribute_value": "Red"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["attribute_name"] == "Color"
    assert data["attribute_value"] == "Red"


@pytest.mark.anyio
async def test_add_item_barcode(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/items/", json={"name": "Barcode Item"}
    )
    item_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/items/{item_id}/barcodes",
        json={"barcode": "123456789012", "format": "EAN-13"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["barcode"] == "123456789012"
    assert data["format"] == "EAN-13"


@pytest.mark.anyio
async def test_get_item_by_barcode(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/items/", json={"name": "Barcode Lookup Item"}
    )
    item_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/items/{item_id}/barcodes",
        json={"barcode": "BARCODE-001"},
    )

    response = await client.get("/api/v1/items/barcode/BARCODE-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == "Barcode Lookup Item"
