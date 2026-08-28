"""Sales capability router: point-of-sale sale completion and management.

Any authenticated user (notably the attendant) can complete, view, search,
and print a sale; cancellation is restricted to manager/admin because it
mutates stock and fiado balances.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.services import sales as service
from app.services.customers import CustomerNotFound
from app.services.inventory import InsufficientStockError, UnknownProductError
from app.services.payments import FiadoLimitExceededError, PaymentError

router = APIRouter(prefix="/sales", tags=["sales"])

DbSession = Annotated[Session, Depends(get_db)]


def _role_dependency(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a role-checked current-user dependency (typed for ``Depends``)."""
    return cast(Callable[..., CurrentUser], require_role(*roles))


attendant_or_higher = _role_dependency(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)
manager_or_higher = _role_dependency(Role.MANAGER, Role.ADMIN)

AttendantDependency = Annotated[CurrentUser, Depends(attendant_or_higher)]
ManagerDependency = Annotated[CurrentUser, Depends(manager_or_higher)]


class SaleItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    pack: bool = False


class PaymentIn(BaseModel):
    method: str
    amount_cents: int = Field(gt=0)
    card_operator: str | None = Field(default=None, max_length=50)
    installments: int | None = Field(default=None, ge=1)


class DeliveryIn(BaseModel):
    street: str | None = Field(default=None, max_length=200)
    number: str | None = Field(default=None, max_length=20)
    district: str | None = Field(default=None, max_length=100)
    complement: str | None = Field(default=None, max_length=200)
    reference: str | None = Field(default=None, max_length=300)


class SaleCreate(BaseModel):
    items: list[SaleItemIn] = Field(min_length=1)
    payments: list[PaymentIn] = Field(min_length=1)
    customer_id: int | None = None
    shift_id: int | None = None
    delivery: DeliveryIn | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=64)


class CancelBody(BaseModel):
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be empty")
        return value


class SaleItemOut(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    unit_price_cents: int
    quantity: int
    pack: bool
    line_total_cents: int


class SalePaymentOut(BaseModel):
    id: int
    method: str
    amount_cents: int
    card_operator: str | None
    installments: int | None


class DeliveryOut(BaseModel):
    id: int
    status: str
    street: str | None
    number: str | None
    district: str | None
    complement: str | None
    reference: str | None


class SaleOut(BaseModel):
    id: int
    customer_id: int | None
    shift_id: int | None
    status: str
    cancelled_reason: str | None
    total_cents: int
    idempotency_key: str | None
    created_at: datetime
    items: list[SaleItemOut]
    payments: list[SalePaymentOut]
    delivery: DeliveryOut | None


def _sale_out(sale) -> SaleOut:
    return SaleOut(
        id=sale.id,
        customer_id=sale.customer_id,
        shift_id=sale.shift_id,
        status=sale.status,
        cancelled_reason=sale.cancelled_reason,
        total_cents=sale.total_cents,
        idempotency_key=sale.idempotency_key,
        created_at=sale.created_at,
        items=[_sale_item_out(item) for item in sale.items],
        payments=[_sale_payment_out(payment) for payment in sale.payments],
        delivery=_delivery_out(sale.delivery) if sale.delivery else None,
    )


def _sale_item_out(item) -> SaleItemOut:
    return SaleItemOut(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product_name,
        unit_price_cents=item.unit_price_cents,
        quantity=item.quantity,
        pack=item.pack,
        line_total_cents=item.line_total_cents,
    )


def _sale_payment_out(payment) -> SalePaymentOut:
    return SalePaymentOut(
        id=payment.id,
        method=payment.method,
        amount_cents=payment.amount_cents,
        card_operator=payment.card_operator,
        installments=payment.installments,
    )


def _delivery_out(delivery) -> DeliveryOut:
    return DeliveryOut(
        id=delivery.id,
        status=delivery.status,
        street=delivery.street,
        number=delivery.number,
        district=delivery.district,
        complement=delivery.complement,
        reference=delivery.reference,
    )


@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def complete(
    body: SaleCreate,
    db: DbSession,
    user: AttendantDependency,
) -> SaleOut:
    """Complete a sale with its items and payments (any authenticated user)."""
    try:
        sale = service.complete_sale(
            db,
            items=[item.model_dump() for item in body.items],
            payments=[payment.model_dump() for payment in body.payments],
            customer_id=body.customer_id,
            shift_id=body.shift_id,
            delivery=body.delivery.model_dump(exclude_none=True) if body.delivery else None,
            idempotency_key=body.idempotency_key,
            actor_id=user.user_id,
        )
    except (UnknownProductError, CustomerNotFound) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InsufficientStockError, FiadoLimitExceededError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (service.SaleError, PaymentError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _sale_out(sale)


@router.get("", response_model=list[SaleOut])
def list_sales(
    db: DbSession,
    user: AttendantDependency,
    customer_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SaleOut]:
    """Search completed sales by customer or creation-date range."""
    return [
        _sale_out(sale)
        for sale in service.search_sales(
            db,
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
    ]


@router.get("/{sale_id}", response_model=SaleOut)
def detail(sale_id: int, db: DbSession, user: AttendantDependency) -> SaleOut:
    """Sale detail with items, payments, and delivery."""
    try:
        return _sale_out(service.get_sale(db, sale_id))
    except service.SaleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{sale_id}/receipt", response_model=list[str])
def receipt(sale_id: int, db: DbSession, user: AttendantDependency) -> list[str]:
    """Non-fiscal receipt lines for printing on a thermal printer."""
    try:
        return service.receipt_lines(db, sale_id)
    except service.SaleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{sale_id}/cancel", response_model=SaleOut)
def cancel(
    sale_id: int,
    body: CancelBody,
    db: DbSession,
    user: ManagerDependency,
) -> SaleOut:
    """Cancel a completed sale, restoring stock and reversing fiado (mgr/admin)."""
    try:
        sale = service.cancel_sale(db, sale_id=sale_id, reason=body.reason, actor_id=user.user_id)
    except service.SaleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except service.SaleError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _sale_out(sale)
