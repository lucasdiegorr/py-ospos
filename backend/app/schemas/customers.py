"""Pydantic schemas for the customers capability.

Money amounts are integer cents (see ``app.domain.money``). The fiado
(credit) profile is optional: a customer with no fiado fields at all has no
profile, which is always allowed. Attempting to set a profile requires at
least one of the three fields (credit limit, interest rate, due period) to be
non-null.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

FIADO_FIELD_NAMES = ("credit_limit_cents", "interest_rate", "due_period_days")

FIADO_REQUIRED_MESSAGE = (
    "fiado profile requires at least one of credit_limit_cents, interest_rate, due_period_days"
)


class CustomerFiadoIn(BaseModel):
    """Optional fiado profile payload; at least one field must be non-null."""

    model_config = ConfigDict(extra="forbid")

    credit_limit_cents: int | None = Field(default=None, ge=0)
    interest_rate: float | None = Field(default=None, ge=0)
    due_period_days: int | None = Field(default=None, gt=0)

    def has_any_field(self) -> bool:
        """Return whether at least one of the three profile fields is set."""
        return any(getattr(self, name) is not None for name in FIADO_FIELD_NAMES)


class CustomerCreate(BaseModel):
    """Payload to register a customer. Only ``name`` is required."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    cpf: str | None = None
    phone: str | None = None

    # Optional / partial address — every field may be empty (reference only).
    street: str | None = None
    number: str | None = None
    district: str | None = None
    complement: str | None = None
    reference: str | None = None

    fiado: CustomerFiadoIn | None = None

    @model_validator(mode="after")
    def _validate_create(self) -> CustomerCreate:
        if not self.name.strip():
            raise ValueError("customer name is required")
        if self.fiado is not None and not self.fiado.has_any_field():
            raise ValueError(FIADO_REQUIRED_MESSAGE)
        return self


class CustomerUpdate(BaseModel):
    """Partial update payload. The ``fiado`` object merges over the current
    profile: fields explicitly present replace stored values, absent fields
    are preserved. The merged profile must still satisfy the at-least-one
    field rule."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    cpf: str | None = None
    phone: str | None = None
    street: str | None = None
    number: str | None = None
    district: str | None = None
    complement: str | None = None
    reference: str | None = None
    fiado: CustomerFiadoIn | None = None


class CustomerOut(BaseModel):
    """Customer representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cpf: str | None
    phone: str | None
    street: str | None
    number: str | None
    district: str | None
    complement: str | None
    reference: str | None
    credit_limit_cents: int | None
    interest_rate: float | None
    due_period_days: int | None
    outstanding_balance_cents: int
    created_at: datetime


class PaymentOut(BaseModel):
    """A single payment attached to a sale (shown in purchase history)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    method: str
    amount_cents: int
    card_operator: str | None
    installments: int | None
    created_at: datetime


class SaleOut(BaseModel):
    """A sale shown in the customer purchase history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_cents: int
    created_at: datetime
    payments: list[PaymentOut]


class CustomerHistoryOut(BaseModel):
    """Customer record plus recent sales and the outstanding fiado balance."""

    customer: CustomerOut
    outstanding_balance_cents: int
    recent_sales: list[SaleOut]
