"""Customer service: registration, search, editing, and fiado profile rules.

The fiado (credit) profile rule is centralized here: a profile is only
created or updated when at least one of the three fields (credit limit,
interest rate, due period) is non-null. ``None`` means "no profile" and is
always allowed, so a sale without a customer (walk-in) is never forced to
carry fiado data by this capability.
"""

from __future__ import annotations

from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.sales import Sale
from app.schemas.customers import (
    FIADO_REQUIRED_MESSAGE,
    CustomerCreate,
    CustomerFiadoIn,
    CustomerUpdate,
)

_OPTIONAL_STRING_FIELDS = (
    "cpf",
    "phone",
    "street",
    "number",
    "district",
    "complement",
    "reference",
)


class CustomerNotFound(LookupError):
    """Raised when a requested customer does not exist."""


class FiadoProfileError(ValueError):
    """Raised when a fiado profile has none of its three fields set."""


def validate_fiado_profile(fiado: CustomerFiadoIn | None) -> None:
    """Reject an explicit profile with none of the three fields set."""
    if fiado is not None and not fiado.has_any_field():
        raise FiadoProfileError(FIADO_REQUIRED_MESSAGE)


def _normalize_optional(value: str | None) -> str | None:
    """Trim optional strings and treat blank values as absent."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _require_name(value: str | None) -> str:
    """Validate that a customer display name is non-blank."""
    stripped = (value or "").strip()
    if not stripped:
        raise ValueError("customer name is required")
    return stripped


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    """Register a customer; only ``name`` is required."""
    validate_fiado_profile(data.fiado)
    customer = Customer(
        name=_require_name(data.name),
        cpf=_normalize_optional(data.cpf),
        phone=_normalize_optional(data.phone),
        street=_normalize_optional(data.street),
        number=_normalize_optional(data.number),
        district=_normalize_optional(data.district),
        complement=_normalize_optional(data.complement),
        reference=_normalize_optional(data.reference),
        credit_limit_cents=data.fiado.credit_limit_cents if data.fiado else None,
        interest_rate=data.fiado.interest_rate if data.fiado else None,
        due_period_days=data.fiado.due_period_days if data.fiado else None,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int) -> Customer:
    """Return a customer by id or raise :class:`CustomerNotFound`."""
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise CustomerNotFound(f"customer {customer_id} not found")
    return customer


def _merge_fiado(customer: Customer, fiado: CustomerFiadoIn) -> CustomerFiadoIn:
    """Merge a partial fiado payload over the current profile.

    Fields explicitly present in the payload replace the stored value; absent
    fields keep their current value. This lets a client raise just the credit
    limit without wiping interest/due period, and it lets the merge result be
    validated against the at-least-one-field rule.
    """
    provided = fiado.model_fields_set
    return CustomerFiadoIn(
        credit_limit_cents=(
            fiado.credit_limit_cents
            if "credit_limit_cents" in provided
            else customer.credit_limit_cents
        ),
        interest_rate=(
            fiado.interest_rate if "interest_rate" in provided else customer.interest_rate
        ),
        due_period_days=(
            fiado.due_period_days if "due_period_days" in provided else customer.due_period_days
        ),
    )


def update_customer(db: Session, customer_id: int, data: CustomerUpdate) -> Customer:
    """Edit a customer's basic data and/or fiado profile."""
    customer = get_customer(db, customer_id)
    provided = data.model_fields_set

    if "name" in provided:
        customer.name = _require_name(data.name)

    for attr in _OPTIONAL_STRING_FIELDS:
        if attr in provided:
            setattr(customer, attr, _normalize_optional(getattr(data, attr)))

    if data.fiado is not None:
        merged = _merge_fiado(customer, data.fiado)
        validate_fiado_profile(merged)
        customer.credit_limit_cents = merged.credit_limit_cents
        customer.interest_rate = merged.interest_rate
        customer.due_period_days = merged.due_period_days

    db.commit()
    db.refresh(customer)
    return customer


def search_customers(db: Session, query: str | None = None, *, limit: int = 50) -> list[Customer]:
    """Search customers by name, CPF, or phone fragment.

    Results are ranked by best match: exact name, name prefix, name fragment,
    then CPF/phone fragment; ties break alphabetically by name.
    """
    statement = db.query(Customer)
    needle = (query or "").strip()
    if needle:
        rank = case(
            (Customer.name == needle, 0),
            (Customer.name.ilike(f"{needle}%"), 1),
            (Customer.name.ilike(f"%{needle}%"), 2),
            (Customer.cpf.ilike(f"%{needle}%"), 3),
            (Customer.phone.ilike(f"%{needle}%"), 4),
            else_=5,
        )
        statement = statement.filter(
            or_(
                Customer.name.ilike(f"%{needle}%"),
                Customer.cpf.ilike(f"%{needle}%"),
                Customer.phone.ilike(f"%{needle}%"),
            )
        ).order_by(rank, Customer.name)
    else:
        statement = statement.order_by(Customer.name)
    return statement.limit(limit).all()


def get_customer_history(
    db: Session, customer_id: int, *, limit: int = 20
) -> tuple[Customer, list[Sale]]:
    """Return a customer and their recent sales, newest first."""
    customer = get_customer(db, customer_id)
    sales = (
        db.query(Sale)
        .filter(Sale.customer_id == customer_id)
        .order_by(Sale.created_at.desc())
        .limit(limit)
        .all()
    )
    return customer, sales
