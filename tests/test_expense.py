import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_create_expense_category(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/expenses/categories",
        json={"name": "Utilities", "description": "Electricity, water, gas"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Utilities"
    assert "id" in data


@pytest.mark.anyio
async def test_list_expense_categories(client: AsyncClient) -> None:
    await client.post("/api/v1/expenses/categories", json={"name": "Supplies"})
    await client.post("/api/v1/expenses/categories", json={"name": "Maintenance"})

    response = await client.get("/api/v1/expenses/categories")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.anyio
async def test_create_expense(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/expenses/",
        json={
            "amount": 150.00,
            "description": "Office supplies",
            "reference_number": "EXP-001",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 150.00
    assert data["description"] == "Office supplies"
    assert data["reference_number"] == "EXP-001"
    assert "id" in data


@pytest.mark.anyio
async def test_list_expenses(client: AsyncClient) -> None:
    await client.post("/api/v1/expenses/", json={"amount": 50.00, "description": "Test 1"})
    await client.post("/api/v1/expenses/", json={"amount": 75.00, "description": "Test 2"})

    response = await client.get("/api/v1/expenses/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.anyio
async def test_get_expense_by_id(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/expenses/", json={"amount": 200.00, "description": "Get test"}
    )
    expense_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/expenses/{expense_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == expense_id
    assert data["amount"] == 200.00


@pytest.mark.anyio
async def test_update_expense(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/expenses/", json={"amount": 100.00, "description": "Update test"}
    )
    expense_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/expenses/{expense_id}",
        json={"amount": 125.00},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 125.00


@pytest.mark.anyio
async def test_delete_expense(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/expenses/", json={"amount": 50.00, "description": "Delete test"}
    )
    expense_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/expenses/{expense_id}")
    assert response.status_code == 204

    get_response = await client.get(f"/api/v1/expenses/{expense_id}")
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_create_cash_up(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/expenses/cash-ups",
        json={
            "expected_cash": 1000.00,
            "actual_cash": 950.00,
            "note": "Cash shortage",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["expected_cash"] == 1000.00
    assert data["actual_cash"] == 950.00
    assert data["variance"] == -50.00


@pytest.mark.anyio
async def test_list_cash_ups(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/expenses/cash-ups",
        json={"expected_cash": 500.00, "actual_cash": 500.00},
    )
    await client.post(
        "/api/v1/expenses/cash-ups",
        json={"expected_cash": 800.00, "actual_cash": 780.00},
    )

    response = await client.get("/api/v1/expenses/cash-ups")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2