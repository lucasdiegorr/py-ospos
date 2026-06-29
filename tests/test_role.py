import pytest
from httpx import AsyncClient

import app.core.auth as auth_module
import app.api.v1.employee as emp_module


# Patch get_effective_permissions in both modules so require_permission passes
# and the employee/me endpoint returns permissions
@pytest.fixture(autouse=True)
def _patch_permissions():
    async def mock_get_effective_permissions(db, employee_id):
        return {
            "admin.roles",
            "admin.permissions",
            "admin.settings",
            "customers.read",
            "items.read",
            "employees.read",
        }

    orig_auth = auth_module.get_effective_permissions
    orig_emp = emp_module.get_effective_permissions
    auth_module.get_effective_permissions = mock_get_effective_permissions
    emp_module.get_effective_permissions = mock_get_effective_permissions
    yield
    auth_module.get_effective_permissions = orig_auth
    emp_module.get_effective_permissions = orig_emp


@pytest.mark.anyio
async def test_list_permissions(client: AsyncClient) -> None:
    response = await client.get("/api/v1/permissions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.anyio
async def test_create_role(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/roles/",
        json={"name": "Test Role", "description": "A test role", "permission_ids": []},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Role"
    assert data["id"] is not None


@pytest.mark.anyio
async def test_create_role_duplicate_name(client: AsyncClient) -> None:
    await client.post("/api/v1/roles/", json={"name": "UniqueRole", "permission_ids": []})
    response = await client.post("/api/v1/roles/", json={"name": "UniqueRole", "permission_ids": []})
    assert response.status_code == 409


@pytest.mark.anyio
async def test_list_roles(client: AsyncClient) -> None:
    await client.post("/api/v1/roles/", json={"name": "Role A", "permission_ids": []})
    await client.post("/api/v1/roles/", json={"name": "Role B", "permission_ids": []})
    response = await client.get("/api/v1/roles/")
    assert response.status_code == 200
    names = [r["name"] for r in response.json()]
    assert "Role A" in names
    assert "Role B" in names


@pytest.mark.anyio
async def test_get_role(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/roles/", json={"name": "Target Role", "permission_ids": []})
    role_id = create_resp.json()["id"]
    response = await client.get(f"/api/v1/roles/{role_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Target Role"


@pytest.mark.anyio
async def test_get_role_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/roles/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_role(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/roles/", json={"name": "Old Name", "permission_ids": []})
    role_id = create_resp.json()["id"]
    response = await client.patch(
        f"/api/v1/roles/{role_id}",
        json={"name": "New Name", "description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Updated description"


@pytest.mark.anyio
async def test_delete_role(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/roles/", json={"name": "Delete Me", "permission_ids": []})
    role_id = create_resp.json()["id"]
    response = await client.delete(f"/api/v1/roles/{role_id}")
    assert response.status_code == 204
    get_resp = await client.get(f"/api/v1/roles/{role_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_assign_employee_roles(client: AsyncClient) -> None:
    role_resp = await client.post("/api/v1/roles/", json={"name": "Assignable Role", "permission_ids": []})
    role_id = role_resp.json()["id"]
    response = await client.post(
        "/api/v1/employees/test-user-id/roles",
        json={"role_ids": [role_id]},
    )
    assert response.status_code == 200


@pytest.mark.anyio
async def test_get_employee_roles(client: AsyncClient) -> None:
    role_resp = await client.post("/api/v1/roles/", json={"name": "Employee Role", "permission_ids": []})
    role_id = role_resp.json()["id"]
    await client.post("/api/v1/employees/test-user-id/roles", json={"role_ids": [role_id]})
    response = await client.get("/api/v1/employees/test-user-id/roles")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_remove_employee_role(client: AsyncClient) -> None:
    role_resp = await client.post("/api/v1/roles/", json={"name": "Removable Role", "permission_ids": []})
    role_id = role_resp.json()["id"]
    await client.post("/api/v1/employees/test-user-id/roles", json={"role_ids": [role_id]})
    response = await client.delete(f"/api/v1/employees/test-user-id/roles/{role_id}")
    assert response.status_code == 204


@pytest.mark.anyio
async def test_employee_me_returns_permissions(client: AsyncClient) -> None:
    response = await client.get("/api/v1/employees/me")
    assert response.status_code == 200
    data = response.json()
    assert "permissions" in data
    assert isinstance(data["permissions"], list)
    assert "admin.roles" in data["permissions"]
