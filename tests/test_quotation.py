import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_create_quotation(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/quotations/",
        json={"comment": "Test quotation"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["comment"] == "Test quotation"
    assert data["employee_id"] == "test-user-id"
    assert "id" in data


@pytest.mark.anyio
async def test_list_quotations(client: AsyncClient) -> None:
    await client.post("/api/v1/quotations/", json={"comment": "Q1"})
    await client.post("/api/v1/quotations/", json={"comment": "Q2"})

    response = await client.get("/api/v1/quotations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.anyio
async def test_get_quotation(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/quotations/", json={"comment": "Get test"}
    )
    qid = create_resp.json()["id"]

    response = await client.get(f"/api/v1/quotations/{qid}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == qid
    assert data["comment"] == "Get test"


@pytest.mark.anyio
async def test_get_quotation_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/quotations/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Quotation not found"


@pytest.mark.anyio
async def test_add_quotation_line(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/quotations/", json={"comment": "Line test"}
    )
    qid = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/quotations/{qid}/lines",
        json={
            "item_name": "Test Item",
            "quantity": 2,
            "unit_price": 10.0,
            "discount_percent": 0,
            "discount_amount": 0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == qid


@pytest.mark.anyio
async def test_add_line_to_non_draft(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/quotations/", json={"comment": "Send then add line"}
    )
    qid = create_resp.json()["id"]

    await client.post(f"/api/v1/quotations/{qid}/send")

    response = await client.post(
        f"/api/v1/quotations/{qid}/lines",
        json={"item_name": "Nope", "quantity": 1, "unit_price": 1.0},
    )
    assert response.status_code == 400
    assert "draft" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_update_quotation(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/quotations/", json={"comment": "Update test"}
    )
    qid = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/quotations/{qid}",
        json={"comment": "Updated"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["comment"] == "Updated"


@pytest.mark.anyio
async def test_delete_quotation(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/quotations/", json={"comment": "Delete test"}
    )
    qid = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/quotations/{qid}")
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/quotations/{qid}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_send_quotation(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/quotations/", json={"comment": "Send test"}
    )
    qid = create_resp.json()["id"]

    response = await client.post(f"/api/v1/quotations/{qid}/send")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
