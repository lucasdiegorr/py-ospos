"""Payment services: method registry, sale payment recording, and shift totals.

The sales capability calls these functions during checkout; this module owns
the payment domain invariants: method availability, split-payment coverage,
fiado credit-limit validation, and per-shift per-method totals.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.payment import PaymentMethod
from app.models.sales import Payment, Sale

# Canonical payment-method keys; also the PaymentMethod.id values.
CASH = "cash"
CARD = "card"
PIX = "pix"
FIADO = "fiado"

# Default registry seeded on first run (see seed_default_payment_methods).
DEFAULT_PAYMENT_METHODS: dict[str, str] = {
    CASH: "Cash",
    CARD: "Card",
    PIX: "PIX",
    FIADO: "Fiado",
}


class PaymentError(Exception):
    """Base class for payment domain violations."""


class PaymentMethodNotFoundError(PaymentError):
    """Raised when referencing an unregistered payment method."""


class PaymentMethodDisabledError(PaymentError):
    """Raised when recording a payment against a disabled method."""


class FiadoLimitExceededError(PaymentError):
    """Raised when a fiado payment would exceed the customer's credit limit."""


def seed_default_payment_methods(db: Session) -> None:
    """Idempotently create the four default payment methods if missing.

    Existing rows (including their enabled state) are left untouched, so this
    is safe to call on every startup.
    """
    for method_id, name in DEFAULT_PAYMENT_METHODS.items():
        if db.get(PaymentMethod, method_id) is None:
            db.add(PaymentMethod(id=method_id, name=name, is_enabled=True))
    db.commit()


def list_payment_methods(db: Session, *, only_enabled: bool = False) -> list[PaymentMethod]:
    """Return registered payment methods, optionally only enabled ones."""
    stmt = select(PaymentMethod).order_by(PaymentMethod.id)
    if only_enabled:
        stmt = stmt.where(PaymentMethod.is_enabled.is_(True))
    return list(db.scalars(stmt))


def get_payment_method(db: Session, method_id: str) -> PaymentMethod | None:
    """Return a payment method by key, or ``None`` if unregistered."""
    return db.get(PaymentMethod, method_id)


def update_payment_method(
    db: Session,
    method_id: str,
    *,
    name: str | None = None,
    is_enabled: bool | None = None,
) -> PaymentMethod:
    """Update a payment method's display name and/or enabled flag."""
    method = db.get(PaymentMethod, method_id)
    if method is None:
        raise PaymentMethodNotFoundError(f"Unknown payment method: {method_id}")
    if name is not None:
        method.name = name
    if is_enabled is not None:
        method.is_enabled = is_enabled
    db.commit()
    return method


def record_payment(
    db: Session,
    *,
    sale: Sale,
    method: str,
    amount_cents: int,
    card_operator: str | None = None,
    installments: int | None = None,
) -> Payment:
    """Record a single payment against a sale.

    The method must be registered and enabled. Card payments store the card
    operator and installment count; those fields are ``None`` for other
    methods. The sale may still be transient (not yet flushed): callers record
    all payments, then run ``validate_payments_cover_total`` before committing.
    """
    if amount_cents <= 0:
        raise PaymentError("Payment amount must be positive")
    method_row = db.get(PaymentMethod, method)
    if method_row is None:
        raise PaymentMethodNotFoundError(f"Unknown payment method: {method}")
    if not method_row.is_enabled:
        raise PaymentMethodDisabledError(f"Payment method is disabled: {method}")
    if method == CARD:
        if installments is not None and installments < 1:
            raise PaymentError("Installments must be a positive integer")
        operator: str | None = card_operator or None
        card_installments: int | None = installments
    else:
        operator = None
        card_installments = None
    payment = Payment(
        sale=sale,
        method=method,
        amount_cents=amount_cents,
        card_operator=operator,
        installments=card_installments,
    )
    db.add(payment)
    return payment


def apply_fiado(
    db: Session,
    *,
    sale: Sale,
    amount_cents: int,
    customer: Customer | None = None,
) -> Payment:
    """Record a fiado payment linked to a customer and raise their balance.

    The customer (the sale's customer when not given) must exist. The
    outstanding balance is increased by ``amount_cents`` after validating it
    stays within the credit limit; customers without a credit limit may buy on
    fiado (per the customers spec).
    """
    if customer is None:
        if sale.customer_id is None:
            raise PaymentError("Fiado requires a registered customer")
        customer = db.get(Customer, sale.customer_id)
    if customer is None:
        raise PaymentError("Fiado requires a registered customer")
    if customer.id is None:
        db.flush()  # persist a transient customer so the sale link has an id
    if sale.customer_id is not None and customer.id != sale.customer_id:
        raise PaymentError("Fiado customer does not match the sale's customer")
    if sale.customer_id is None:
        sale.customer_id = customer.id
    if customer.credit_limit_cents is not None:
        projected = customer.outstanding_balance_cents + amount_cents
        if projected > customer.credit_limit_cents:
            raise FiadoLimitExceededError("Fiado payment would exceed the customer's credit limit")
    payment = record_payment(db, sale=sale, method=FIADO, amount_cents=amount_cents)
    customer.outstanding_balance_cents += amount_cents
    return payment


def validate_payments_cover_total(db: Session, sale: Sale) -> int:
    """Return the total paid on a sale; raise if it differs from the total.

    Used by the sales capability to complete a sale only when the recorded
    payments exactly cover the cart total.
    """
    paid = _sum_paid(db, sale)
    if paid != sale.total_cents:
        raise PaymentError(f"Payments sum to {paid} but the sale total is {sale.total_cents}")
    return paid


def payment_totals_by_method(db: Session, shift_id: int) -> dict[str, int]:
    """Return ``{method: total_cents}`` for completed sales in a shift."""
    rows = db.execute(
        select(Payment.method, func.coalesce(func.sum(Payment.amount_cents), 0))
        .join(Sale, Payment.sale_id == Sale.id)
        .where(Sale.shift_id == shift_id, Sale.status == "completed")
        .group_by(Payment.method)
        .order_by(Payment.method)
    ).all()
    return {method: int(total or 0) for method, total in rows}


def _sum_paid(db: Session, sale: Sale) -> int:
    """Return the sum of a sale's payments, flushing pending ones first."""
    db.flush()  # include payments recorded in the current unit of work
    total = db.scalar(
        select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(Payment.sale_id == sale.id)
    )
    return int(total or 0)
