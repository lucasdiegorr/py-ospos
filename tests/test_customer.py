import pytest
from httpx import AsyncClient

from app.main import app
from app.core.auth import get_current_user


class MockNonAdmin:
    id = "non-admin-id"
    username = "testuser"
    first_name = "Test"
    last_name = "User"
    email = "test@example.com"
    is_active = True


CUSTOMER_URL = "/api/v1/customers"


@pytest.mark.anyio
async def test_create_customer(client: AsyncClient) -> None:
    response = await client.post(
        f"{CUSTOMER_URL}/",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "1234567890",
            "type": "customer",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["email"] == "john@example.com"
    assert "id" in data


@pytest.mark.anyio
async def test_list_customers(client: AsyncClient) -> None:
    await client.post(f"{CUSTOMER_URL}/", json={"first_name": "Alice", "last_name": "Smith"})
    await client.post(f"{CUSTOMER_URL}/", json={"first_name": "Bob", "last_name": "Jones"})

    response = await client.get(f"{CUSTOMER_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.anyio
async def test_list_customers_with_search(client: AsyncClient) -> None:
    await client.post(
        f"{CUSTOMER_URL}/",
        json={"first_name": "Alice", "last_name": "Smith", "email": "alice@example.com"},
    )
    await client.post(
        f"{CUSTOMER_URL}/",
        json={"first_name": "Bob", "last_name": "Jones", "email": "bob@example.com"},
    )

    response = await client.get(f"{CUSTOMER_URL}/", params={"search": "Alice"})
    assert response.status_code == 200


@pytest.mark.anyio
async def test_list_customers_by_type(client: AsyncClient) -> None:
    await client.post(
        f"{CUSTOMER_URL}/",
        json={"first_name": "Supplier", "last_name": "One", "type": "supplier"},
    )
    await client.post(
        f"{CUSTOMER_URL}/",
        json={"first_name": "Customer", "last_name": "One", "type": "customer"},
    )

    response = await client.get(f"{CUSTOMER_URL}/", params={"customer_type": "supplier"})
    assert response.status_code == 200


@pytest.mark.anyio
async def test_get_customer(client: AsyncClient) -> None:
    create_response = await client.post(
        f"{CUSTOMER_URL}/",
        json={"first_name": "Jane", "last_name": "Doe"},
    )
    customer_id = create_response.json()["id"]

    response = await client.get(f"{CUSTOMER_URL}/{customer_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == customer_id
    assert data["first_name"] == "Jane"


@pytest.mark.anyio
async def test_get_customer_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{CUSTOMER_URL}/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


@pytest.mark.anyio
async def test_update_customer(client: AsyncClient) -> None:
    create_response = await client.post(
        f"{CUSTOMER_URL}/",
        json={"first_name": "Old", "last_name": "Name"},
    )
    customer_id = create_response.json()["id"]

    response = await client.patch(
        f"{CUSTOMER_URL}/{customer_id}",
        json={"first_name": "Updated", "company_name": "New Corp"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["company_name"] == "New Corp"


@pytest.mark.anyio
async def test_delete_customer(client: AsyncClient) -> None:
    create_response = await client.post(
        f"{CUSTOMER_URL}/",
        json={"first_name": "Delete", "last_name": "Me"},
    )
    customer_id = create_response.json()["id"]

    response = await client.delete(f"{CUSTOMER_URL}/{customer_id}")
    assert response.status_code == 204

    get_response = await client.get(f"{CUSTOMER_URL}/{customer_id}")
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_delete_customer_forbidden(client: AsyncClient) -> None:
    async def mock_get_non_admin():
        return MockNonAdmin()

    app.dependency_overrides[get_current_user] = mock_get_non_admin

    response = await client.delete(f"{CUSTOMER_URL}/some-id")
    assert response.status_code == 403
