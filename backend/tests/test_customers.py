"""Tests for the customers capability.

Pure rules (fiado validation) are unit-tested without a database. The
remaining scenarios run through the HTTP API against a Postgres database
inside a transaction that is rolled back after each test (see ``conftest``),
so no data is persisted. Because the sales capability is not implemented yet,
purchase history and walk-in sales are exercised at the data layer using the
``Sale``/``Payment`` models directly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.sales import Payment, Sale
from app.schemas.customers import CustomerFiadoIn
from app.services.customers import FiadoProfileError, validate_fiado_profile

# ---------------------------------------------------------------------------
# Pure fiado profile validation (no database)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fiado",
    [
        CustomerFiadoIn(credit_limit_cents=50000),
        CustomerFiadoIn(interest_rate=2.5),
        CustomerFiadoIn(due_period_days=30),
        CustomerFiadoIn(credit_limit_cents=0),
        None,  # no profile requested is always allowed
    ],
)
def test_fiado_profile_with_one_field_accepted(fiado: CustomerFiadoIn | None) -> None:
    validate_fiado_profile(fiado)  # should not raise


def test_fiado_profile_with_no_fields_rejected() -> None:
    with pytest.raises(FiadoProfileError):
        validate_fiado_profile(CustomerFiadoIn())


# ---------------------------------------------------------------------------
# Register customer (minimal data / identifiers / partial address)
# ---------------------------------------------------------------------------


def test_register_by_name_only(client: TestClient) -> None:
    response = client.post("/customers", json={"name": "Maria Silva"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Maria Silva"
    assert body["cpf"] is None
    assert body["phone"] is None
    assert body["credit_limit_cents"] is None
    assert body["interest_rate"] is None
    assert body["due_period_days"] is None
    assert body["outstanding_balance_cents"] == 0


def test_register_with_identifiers(client: TestClient) -> None:
    response = client.post(
        "/customers",
        json={"name": "Joao Santos", "cpf": "123.456.789-00", "phone": "(11) 99999-0000"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["cpf"] == "123.456.789-00"
    assert body["phone"] == "(11) 99999-0000"


def test_partial_address_reference_only_accepted(client: TestClient) -> None:
    response = client.post(
        "/customers",
        json={"name": "Padaria Estrela", "reference": "Ao lado da praca"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["reference"] == "Ao lado da praca"
    assert body["street"] is None
    assert body["number"] is None


def test_blank_name_rejected(client: TestClient) -> None:
    response = client.post("/customers", json={"name": "   "})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Fiado profile on create
# ---------------------------------------------------------------------------


def test_fiado_profile_with_only_credit_limit_accepted(client: TestClient) -> None:
    response = client.post(
        "/customers",
        json={"name": "Carlos Lima", "fiado": {"credit_limit_cents": 100000}},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["credit_limit_cents"] == 100000
    assert body["interest_rate"] is None
    assert body["due_period_days"] is None


def test_fiado_profile_with_only_interest_rate_accepted(client: TestClient) -> None:
    response = client.post(
        "/customers",
        json={"name": "Ana Costa", "fiado": {"interest_rate": 2.5}},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["interest_rate"] == 2.5
    assert body["credit_limit_cents"] is None
    assert body["due_period_days"] is None


def test_fiado_profile_with_only_due_period_accepted(client: TestClient) -> None:
    response = client.post(
        "/customers",
        json={"name": "Ze da Esquina", "fiado": {"due_period_days": 15}},
    )
    assert response.status_code == 201
    assert response.json()["due_period_days"] == 15


def test_api_fiado_profile_with_no_fields_rejected(client: TestClient) -> None:
    response = client.post("/customers", json={"name": "Sem Perfil", "fiado": {}})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Search customers (name / CPF / phone)
# ---------------------------------------------------------------------------


def test_search_by_name_fragment_orders_best_match(client: TestClient) -> None:
    client.post("/customers", json={"name": "Maria Silva"})
    client.post("/customers", json={"name": "Joao Maria"})
    client.post("/customers", json={"name": "Marcos Pereira"})

    response = client.get("/customers", params={"q": "maria"})
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert names[0] == "Maria Silva"  # best match first
    assert set(names) == {"Maria Silva", "Joao Maria"}


def test_search_by_cpf(client: TestClient) -> None:
    client.post("/customers", json={"name": "Rita", "cpf": "111.222.333-44"})
    response = client.get("/customers", params={"q": "111.222"})
    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Rita"]


def test_search_by_phone(client: TestClient) -> None:
    client.post("/customers", json={"name": "Paulo", "phone": "11987654321"})
    response = client.get("/customers", params={"q": "98765"})
    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Paulo"]


def test_list_all_customers_ordered_by_name(client: TestClient) -> None:
    client.post("/customers", json={"name": "Bruno"})
    client.post("/customers", json={"name": "Ana"})
    response = client.get("/customers")
    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Ana", "Bruno"]


# ---------------------------------------------------------------------------
# Edit customer and fiado profile
# ---------------------------------------------------------------------------


def test_edit_customer_and_fiado_profile(client: TestClient) -> None:
    created = client.post(
        "/customers",
        json={
            "name": "Antonio",
            "fiado": {
                "credit_limit_cents": 50000,
                "interest_rate": 1.0,
                "due_period_days": 30,
            },
        },
    ).json()
    customer_id = created["id"]

    response = client.patch(
        f"/customers/{customer_id}",
        json={
            "name": "Antonio Ferreira",
            "phone": "(11) 90000-1111",
            "fiado": {"credit_limit_cents": 75000},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Antonio Ferreira"
    assert body["phone"] == "(11) 90000-1111"
    assert body["credit_limit_cents"] == 75000
    # Merge semantics: untouched fiado fields are preserved.
    assert body["interest_rate"] == 1.0
    assert body["due_period_days"] == 30


def test_update_cannot_wipe_whole_profile(client: TestClient) -> None:
    created = client.post(
        "/customers", json={"name": "Sem Limite", "fiado": {"credit_limit_cents": 100}}
    ).json()
    # Nulling the only profile field would leave the profile all-empty -> rejected.
    response = client.patch(
        f"/customers/{created['id']}", json={"fiado": {"credit_limit_cents": None}}
    )
    assert response.status_code == 422


def test_update_cannot_create_empty_profile(client: TestClient) -> None:
    created = client.post("/customers", json={"name": "Novo"}).json()
    response = client.patch(f"/customers/{created['id']}", json={"fiado": {}})
    assert response.status_code == 422


def test_get_customer_not_found(client: TestClient) -> None:
    assert client.get("/customers/999999").status_code == 404


# ---------------------------------------------------------------------------
# Anonymous sale (walk-in) — data layer: a sale must not require a customer
# ---------------------------------------------------------------------------


def test_sale_customer_is_optional() -> None:
    assert Sale.__table__.c.customer_id.nullable is True


def test_anonymous_sale_stored_without_customer(client: TestClient, db_session) -> None:
    sale = Sale(status="completed", total_cents=1500)
    db_session.add(sale)
    db_session.commit()
    assert sale.customer_id is None
    assert db_session.get(Sale, sale.id) is not None


# ---------------------------------------------------------------------------
# Purchase history and outstanding fiado balance
# ---------------------------------------------------------------------------


def test_history_and_balance(client: TestClient, db_session) -> None:
    created = client.post(
        "/customers",
        json={"name": "Loja do Ze", "fiado": {"due_period_days": 15}},
    ).json()
    customer_id = created["id"]

    now = datetime.now(UTC)
    older = Sale(
        customer_id=customer_id,
        status="completed",
        total_cents=4000,
        created_at=now - timedelta(hours=2),
    )
    newer = Sale(customer_id=customer_id, status="completed", total_cents=8500, created_at=now)
    db_session.add_all([older, newer])
    db_session.flush()
    db_session.add(Payment(sale_id=older.id, method="cash", amount_cents=4000))
    db_session.add(Payment(sale_id=newer.id, method="fiado", amount_cents=8500))
    db_session.commit()

    response = client.get(f"/customers/{customer_id}/history")
    assert response.status_code == 200
    body = response.json()
    assert body["customer"]["name"] == "Loja do Ze"
    assert body["customer"]["due_period_days"] == 15
    # Outstanding balance is the customer's stored field; it is maintained by
    # the sales/payments capability, so here it reflects the initial value.
    assert body["outstanding_balance_cents"] == 0
    assert [s["total_cents"] for s in body["recent_sales"]] == [8500, 4000]
    assert body["recent_sales"][0]["payments"][0]["method"] == "fiado"


# ---------------------------------------------------------------------------
# RBAC: endpoints require an authenticated user
# ---------------------------------------------------------------------------


def test_requires_authentication() -> None:
    with TestClient(app) as test_client:
        assert test_client.get("/customers").status_code == 401
