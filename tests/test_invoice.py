import pytest
from httpx import AsyncClient

from app.core.auth import get_db
from app.main import app


@pytest.mark.anyio
async def test_create_invoice(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/invoices/",
        json={"comment": "Test invoice"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["comment"] == "Test invoice"
    assert data["invoice_number"].startswith("INV-")
    assert "id" in data


@pytest.mark.anyio
async def test_list_invoices(client: AsyncClient) -> None:
    await client.post("/api/v1/invoices/", json={"comment": "Invoice 1"})
    await client.post("/api/v1/invoices/", json={"comment": "Invoice 2"})

    response = await client.get("/api/v1/invoices/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.anyio
async def test_get_invoice(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={"comment": "Get test"})
    invoice_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/invoices/{invoice_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == invoice_id
    assert data["comment"] == "Get test"


@pytest.mark.anyio
async def test_get_invoice_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/invoices/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Invoice not found"


@pytest.mark.anyio
async def test_add_invoice_line(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={})
    invoice_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/invoices/{invoice_id}/lines",
        json={
            "item_name": "Widget",
            "quantity": 2,
            "unit_price": 10.00,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == invoice_id


@pytest.mark.anyio
async def test_add_invoice_line_to_non_draft(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={})
    invoice_id = create_resp.json()["id"]

    await client.post(f"/api/v1/invoices/{invoice_id}/void")

    response = await client.post(
        f"/api/v1/invoices/{invoice_id}/lines",
        json={"item_name": "Widget", "quantity": 1, "unit_price": 10.00},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Can only add lines to draft invoices"


@pytest.mark.anyio
async def test_update_invoice(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={"comment": "Original"})
    invoice_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/invoices/{invoice_id}",
        json={"comment": "Updated comment", "discount_amount": 25.00},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["comment"] == "Updated comment"
    assert data["discount_amount"] == 25.00


@pytest.mark.anyio
async def test_add_invoice_payment(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={})
    invoice_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={
            "payment_type": "cash",
            "amount": 100.00,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount_paid"] == 100.00
    assert data["status"] == "paid"
    assert data["balance_due"] == 0


@pytest.mark.anyio
async def test_add_payment_to_paid_invoice(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={})
    invoice_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"payment_type": "cash", "amount": 100.00},
    )

    response = await client.post(
        f"/api/v1/invoices/{invoice_id}/payments",
        json={"payment_type": "card", "amount": 50.00},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invoice already paid"


@pytest.mark.anyio
async def test_send_invoice(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={})
    invoice_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/invoices/{invoice_id}/lines",
        json={"item_name": "Widget", "quantity": 1, "unit_price": 50.00},
    )

    gen = app.dependency_overrides[get_db]()
    session = await gen.__anext__()
    invoice = session._data.get("invoices", {}).get(invoice_id)
    line = list(session._data.get("invoice_lines", {}).values())[-1]
    invoice.lines = [line]
    await gen.aclose()

    response = await client.post(f"/api/v1/invoices/{invoice_id}/send")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"


@pytest.mark.anyio
async def test_send_invoice_without_lines(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={})
    invoice_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/invoices/{invoice_id}/send")
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot send invoice without lines"


@pytest.mark.anyio
async def test_void_invoice(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={})
    invoice_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/invoices/{invoice_id}/void")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "voided"


@pytest.mark.anyio
async def test_void_already_voided(client: AsyncClient) -> None:
    create_resp = await client.post("/api/v1/invoices/", json={})
    invoice_id = create_resp.json()["id"]

    await client.post(f"/api/v1/invoices/{invoice_id}/void")

    response = await client.post(f"/api/v1/invoices/{invoice_id}/void")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invoice already voided"


@pytest.mark.anyio
async def test_create_credit_note(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/invoices/credit-notes",
        json={
            "amount": 250.00,
            "reason": "Customer returned damaged item",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["credit_note_number"].startswith("CN-")
    assert data["amount"] == 250.00
    assert data["reason"] == "Customer returned damaged item"
    assert data["status"] == "active"
    assert "id" in data
