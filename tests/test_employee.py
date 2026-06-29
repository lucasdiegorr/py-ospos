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


EMPLOYEE_URL = "/api/v1/employees"


@pytest.mark.anyio
async def test_create_employee(client: AsyncClient) -> None:
    response = await client.post(
        f"{EMPLOYEE_URL}/",
        json={
            "username": "newemployee",
            "password": "password123",
            "first_name": "New",
            "last_name": "Employee",
            "email": "new@example.com",
            "phone": "1234567890",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newemployee"
    assert data["first_name"] == "New"
    assert data["last_name"] == "Employee"
    assert data["email"] == "new@example.com"
    assert "id" in data


@pytest.mark.anyio
async def test_create_employee_forbidden(client: AsyncClient) -> None:
    async def mock_get_non_admin():
        return MockNonAdmin()

    app.dependency_overrides[get_current_user] = mock_get_non_admin

    response = await client.post(
        f"{EMPLOYEE_URL}/",
        json={
            "username": "hacker",
            "password": "password123",
            "first_name": "Hacker",
            "last_name": "Man",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


@pytest.mark.anyio
async def test_get_current_employee(client: AsyncClient) -> None:
    response = await client.get(f"{EMPLOYEE_URL}/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.anyio
async def test_get_employee(client: AsyncClient) -> None:
    create_response = await client.post(
        f"{EMPLOYEE_URL}/",
        json={
            "username": "findme",
            "password": "password123",
            "first_name": "Find",
            "last_name": "Me",
        },
    )
    employee_id = create_response.json()["id"]

    response = await client.get(f"{EMPLOYEE_URL}/{employee_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == employee_id
    assert data["username"] == "findme"


@pytest.mark.anyio
async def test_get_employee_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{EMPLOYEE_URL}/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"


@pytest.mark.anyio
async def test_update_employee(client: AsyncClient) -> None:
    create_response = await client.post(
        f"{EMPLOYEE_URL}/",
        json={
            "username": "updatable",
            "password": "password123",
            "first_name": "Old",
            "last_name": "Name",
        },
    )
    employee_id = create_response.json()["id"]

    response = await client.patch(
        f"{EMPLOYEE_URL}/{employee_id}",
        json={"first_name": "Updated", "last_name": "Employee"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Employee"


@pytest.mark.anyio
async def test_update_employee_self(client: AsyncClient) -> None:
    create_response = await client.post(
        f"{EMPLOYEE_URL}/",
        json={
            "username": "selfupdate",
            "password": "password123",
            "first_name": "Self",
            "last_name": "Updater",
        },
    )
    employee_id = create_response.json()["id"]

    class MockSelfNonAdmin:
        id = employee_id
        username = "selfupdate"
        first_name = "Self"
        last_name = "Updater"
        email = None
        is_active = True

    async def mock_get_self():
        return MockSelfNonAdmin()

    app.dependency_overrides[get_current_user] = mock_get_self

    response = await client.patch(
        f"{EMPLOYEE_URL}/{employee_id}",
        json={"first_name": "UpdatedSelf"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "UpdatedSelf"


@pytest.mark.anyio
async def test_update_employee_forbidden(client: AsyncClient) -> None:
    create_response = await client.post(
        f"{EMPLOYEE_URL}/",
        json={
            "username": "other",
            "password": "password123",
            "first_name": "Other",
            "last_name": "Employee",
        },
    )
    employee_id = create_response.json()["id"]

    async def mock_get_non_admin():
        return MockNonAdmin()

    app.dependency_overrides[get_current_user] = mock_get_non_admin

    response = await client.patch(
        f"{EMPLOYEE_URL}/{employee_id}",
        json={"first_name": "Hacked"},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_delete_employee(client: AsyncClient) -> None:
    create_response = await client.post(
        f"{EMPLOYEE_URL}/",
        json={
            "username": "todelete",
            "password": "password123",
            "first_name": "Delete",
            "last_name": "Me",
        },
    )
    employee_id = create_response.json()["id"]

    response = await client.delete(f"{EMPLOYEE_URL}/{employee_id}")
    assert response.status_code == 204

    get_response = await client.get(f"{EMPLOYEE_URL}/{employee_id}")
    assert get_response.status_code == 200


@pytest.mark.anyio
async def test_delete_employee_forbidden(client: AsyncClient) -> None:
    async def mock_get_non_admin():
        return MockNonAdmin()

    app.dependency_overrides[get_current_user] = mock_get_non_admin

    response = await client.delete(f"{EMPLOYEE_URL}/some-id")
    assert response.status_code == 403
