"""Tests for the payments capability (specs/payments/spec.md)."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers all models on Base.metadata)
from app.core.security import CurrentUser, Role
from app.db import Base
from app.domain.money import to_cents
from app.models.customer import Customer
from app.models.payment import PaymentMethod
from app.models.sales import Sale
from app.services.payments import (
    FiadoLimitExceededError,
    PaymentError,
    PaymentMethodDisabledError,
    apply_fiado,
    list_payment_methods,
    payment_totals_by_method,
    record_payment,
    seed_default_payment_methods,
    update_payment_method,
    validate_payments_cover_total,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def make_customer(db: Session, *, credit_limit_cents: int | None = None) -> Customer:
    customer = Customer(name="Maria", credit_limit_cents=credit_limit_cents)
    db.add(customer)
    db.flush()
    return customer


def make_sale(
    db: Session,
    *,
    total_cents: int,
    customer_id: int | None = None,
    status: str = "completed",
    shift_id: int | None = None,
) -> Sale:
    sale = Sale(
        total_cents=total_cents,
        customer_id=customer_id,
        status=status,
        shift_id=shift_id,
    )
    db.add(sale)
    db.flush()
    return sale


# --- Requirement: Supported payment methods -------------------------------


def test_seed_creates_four_default_methods(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    methods = list_payment_methods(db_session)
    assert [m.id for m in methods] == ["card", "cash", "fiado", "pix"]
    assert all(m.is_enabled for m in methods)
    # Re-seeding is idempotent and does not create duplicates.
    seed_default_payment_methods(db_session)
    assert len(list_payment_methods(db_session)) == 4


def test_checkout_offers_all_enabled_methods(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    enabled = list_payment_methods(db_session, only_enabled=True)
    assert {m.id for m in enabled} == {"cash", "card", "pix", "fiado"}


# --- Requirement: Payment method registry ---------------------------------


def test_disable_method_not_offered_at_checkout(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    update_payment_method(db_session, "fiado", is_enabled=False)
    enabled = list_payment_methods(db_session, only_enabled=True)
    assert "fiado" not in {m.id for m in enabled}

    customer = make_customer(db_session, credit_limit_cents=to_cents("100.00"))
    sale = make_sale(db_session, total_cents=to_cents("50.00"), customer_id=customer.id)
    with pytest.raises(PaymentMethodDisabledError):
        apply_fiado(db_session, sale=sale, amount_cents=to_cents("50.00"))
    assert customer.outstanding_balance_cents == 0


def test_re_enable_method_offered_again(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    update_payment_method(db_session, "fiado", is_enabled=False)
    update_payment_method(db_session, "fiado", is_enabled=True)
    enabled = list_payment_methods(db_session, only_enabled=True)
    assert "fiado" in {m.id for m in enabled}


def test_seed_preserves_existing_enabled_state(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    update_payment_method(db_session, "fiado", is_enabled=False)
    seed_default_payment_methods(db_session)  # must not re-enable a disabled method
    fiado = db_session.get(PaymentMethod, "fiado")
    assert fiado is not None and not fiado.is_enabled


def test_update_method_rename(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    updated = update_payment_method(db_session, "pix", name="PIX Instantâneo")
    assert updated.name == "PIX Instantâneo"


def test_update_unknown_method_raises(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    with pytest.raises(PaymentError):
        update_payment_method(db_session, "boleto", is_enabled=True)


# --- Requirement: Record payment on a sale --------------------------------


def test_single_cash_payment(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("50.00"))
    payment = record_payment(db_session, sale=sale, method="cash", amount_cents=to_cents("50.00"))
    assert validate_payments_cover_total(db_session, sale) == to_cents("50.00")
    assert payment.method == "cash"
    assert payment.amount_cents == to_cents("50.00")
    assert payment.card_operator is None
    assert payment.installments is None


def test_split_payment_sums_to_total(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("50.00"))
    record_payment(db_session, sale=sale, method="cash", amount_cents=to_cents("30.00"))
    record_payment(db_session, sale=sale, method="pix", amount_cents=to_cents("20.00"))
    assert validate_payments_cover_total(db_session, sale) == to_cents("50.00")
    assert len(sale.payments) == 2


def test_partial_payment_blocked(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("50.00"))
    record_payment(db_session, sale=sale, method="cash", amount_cents=to_cents("30.00"))
    with pytest.raises(PaymentError, match="Payments sum to"):
        validate_payments_cover_total(db_session, sale)


def test_card_installment_records_operator_and_count(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("150.00"))
    payment = record_payment(
        db_session,
        sale=sale,
        method="card",
        amount_cents=to_cents("150.00"),
        card_operator="Visa",
        installments=3,
    )
    assert payment.card_operator == "Visa"
    assert payment.installments == 3
    assert validate_payments_cover_total(db_session, sale) == to_cents("150.00")


def test_non_card_method_ignores_card_fields(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("50.00"))
    payment = record_payment(
        db_session,
        sale=sale,
        method="cash",
        amount_cents=to_cents("50.00"),
        card_operator="Visa",
        installments=3,
    )
    assert payment.card_operator is None
    assert payment.installments is None


def test_record_payment_on_transient_sale(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = Sale(total_cents=to_cents("50.00"))  # not yet persisted
    record_payment(db_session, sale=sale, method="cash", amount_cents=to_cents("50.00"))
    assert validate_payments_cover_total(db_session, sale) == to_cents("50.00")
    assert sale.id is not None  # flushed by the validation step
    assert len(sale.payments) == 1


def test_record_payment_rejects_non_positive_amount(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("0.00"))
    with pytest.raises(PaymentError, match="positive"):
        record_payment(db_session, sale=sale, method="cash", amount_cents=0)


# --- Requirement: Fiado payment linkage -----------------------------------


def test_fiado_adds_to_balance(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    customer = make_customer(db_session, credit_limit_cents=to_cents("100.00"))
    sale = make_sale(db_session, total_cents=to_cents("100.00"), customer_id=customer.id)
    apply_fiado(db_session, sale=sale, amount_cents=to_cents("100.00"))
    assert customer.outstanding_balance_cents == to_cents("100.00")
    assert validate_payments_cover_total(db_session, sale) == to_cents("100.00")
    assert sale.customer_id == customer.id


def test_fiado_limit_exceeded_refused(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    customer = make_customer(db_session, credit_limit_cents=to_cents("100.00"))
    sale = make_sale(db_session, total_cents=to_cents("100.01"), customer_id=customer.id)
    with pytest.raises(FiadoLimitExceededError):
        apply_fiado(db_session, sale=sale, amount_cents=to_cents("100.01"))
    assert customer.outstanding_balance_cents == 0
    assert len(sale.payments) == 0


def test_fiado_without_limit_allowed(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    customer = make_customer(db_session)  # no credit limit
    sale = make_sale(db_session, total_cents=to_cents("50.00"), customer_id=customer.id)
    apply_fiado(db_session, sale=sale, amount_cents=to_cents("50.00"))
    assert customer.outstanding_balance_cents == to_cents("50.00")


def test_fiado_requires_customer(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("50.00"))  # walk-in sale
    with pytest.raises(PaymentError, match="requires a registered customer"):
        apply_fiado(db_session, sale=sale, amount_cents=to_cents("50.00"))


def test_fiado_customer_mismatch_refused(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    customer = make_customer(db_session, credit_limit_cents=to_cents("100.00"))
    other = make_customer(db_session, credit_limit_cents=to_cents("100.00"))
    sale = make_sale(db_session, total_cents=to_cents("50.00"), customer_id=customer.id)
    with pytest.raises(PaymentError, match="does not match"):
        apply_fiado(db_session, sale=sale, amount_cents=to_cents("50.00"), customer=other)


# --- Requirement: PIX without integration ---------------------------------


def test_pix_registered_manually(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("20.00"))
    payment = record_payment(db_session, sale=sale, method="pix", amount_cents=to_cents("20.00"))
    assert payment.method == "pix"
    assert validate_payments_cover_total(db_session, sale) == to_cents("20.00")


# --- Requirement: Payment totals per shift --------------------------------


def test_shift_totals_by_method(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    cash_sale = make_sale(db_session, total_cents=to_cents("50.00"), shift_id=1)
    pix_sale = make_sale(db_session, total_cents=to_cents("20.00"), shift_id=1)
    other_sale = make_sale(db_session, total_cents=to_cents("10.00"), shift_id=2)
    record_payment(db_session, sale=cash_sale, method="cash", amount_cents=to_cents("50.00"))
    record_payment(db_session, sale=pix_sale, method="pix", amount_cents=to_cents("20.00"))
    record_payment(db_session, sale=other_sale, method="cash", amount_cents=to_cents("10.00"))
    db_session.commit()
    assert payment_totals_by_method(db_session, 1) == {
        "cash": to_cents("50.00"),
        "pix": to_cents("20.00"),
    }


def test_shift_totals_exclude_cancelled_sales(db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    completed = make_sale(db_session, total_cents=to_cents("50.00"), shift_id=1)
    cancelled = make_sale(db_session, total_cents=to_cents("30.00"), status="cancelled", shift_id=1)
    record_payment(db_session, sale=completed, method="cash", amount_cents=to_cents("50.00"))
    record_payment(db_session, sale=cancelled, method="pix", amount_cents=to_cents("30.00"))
    db_session.commit()
    assert payment_totals_by_method(db_session, 1) == {"cash": to_cents("50.00")}


# --- Router: method registry and totals ------------------------------------


@pytest.fixture()
def client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    from app.api.routers.payments import current_admin, current_user
    from app.db import get_db
    from app.main import app

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def fake_user() -> CurrentUser:
        return CurrentUser(user_id=1, username="attendant", role=Role.ATTENDANT)

    def fake_admin() -> CurrentUser:
        return CurrentUser(user_id=2, username="admin", role=Role.ADMIN)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = fake_user
    app.dependency_overrides[current_admin] = fake_admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_methods_endpoint(client: TestClient, db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    response = client.get("/payment-methods")
    assert response.status_code == 200
    methods = response.json()
    assert {m["id"] for m in methods} == {"cash", "card", "pix", "fiado"}
    assert all(m["is_enabled"] for m in methods)


def test_enabled_only_endpoint(client: TestClient, db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    update_payment_method(db_session, "fiado", is_enabled=False)
    response = client.get("/payment-methods", params={"enabled": True})
    assert response.status_code == 200
    assert {m["id"] for m in response.json()} == {"cash", "card", "pix"}


def test_disable_method_endpoint(client: TestClient, db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    response = client.patch("/payment-methods/fiado", json={"is_enabled": False})
    assert response.status_code == 200
    assert response.json()["is_enabled"] is False
    fiado = db_session.get(PaymentMethod, "fiado")
    assert fiado is not None and not fiado.is_enabled


def test_update_method_endpoint_rename(client: TestClient, db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    response = client.patch("/payment-methods/pix", json={"name": "PIX Instantâneo"})
    assert response.status_code == 200
    assert response.json()["name"] == "PIX Instantâneo"


def test_update_method_not_found(client: TestClient, db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    response = client.patch("/payment-methods/boleto", json={"is_enabled": True})
    assert response.status_code == 404


def test_shift_totals_endpoint(client: TestClient, db_session: Session) -> None:
    seed_default_payment_methods(db_session)
    sale = make_sale(db_session, total_cents=to_cents("50.00"), shift_id=7)
    record_payment(db_session, sale=sale, method="cash", amount_cents=to_cents("50.00"))
    db_session.commit()
    response = client.get("/shifts/7/payment-totals")
    assert response.status_code == 200
    assert response.json() == {"cash": 5000}
