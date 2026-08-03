"""Payments capability router: method registry and shift payment totals.

The checkout flow itself lives in the sales capability; this module exposes
the payment-method registry (list, enable/disable/rename) and the per-shift
per-method payment totals used by shift closing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.models.payment import PaymentMethod
from app.services.payments import (
    PaymentMethodNotFoundError,
    list_payment_methods,
    payment_totals_by_method,
    update_payment_method,
)

router = APIRouter(tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]


def _role_dependency(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a role-checked current-user dependency (typed for ``Depends``)."""
    return cast(Callable[..., CurrentUser], require_role(*roles))


current_user = _role_dependency(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)
current_admin = _role_dependency(Role.ADMIN)

CurrentUserDependency = Annotated[CurrentUser, Depends(current_user)]
AdminDependency = Annotated[CurrentUser, Depends(current_admin)]


class PaymentMethodOut(BaseModel):
    """Payment method as returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    is_enabled: bool


class PaymentMethodUpdate(BaseModel):
    """Fields an admin may change on a payment method."""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    is_enabled: bool | None = None


@router.get("/payment-methods", response_model=list[PaymentMethodOut])
def list_methods(
    db: DbSession,
    user: CurrentUserDependency,
    enabled: bool | None = None,
) -> list[PaymentMethod]:
    """List payment methods; pass ``?enabled=true`` for checkout methods."""
    return list_payment_methods(db, only_enabled=bool(enabled))


@router.patch("/payment-methods/{method_id}", response_model=PaymentMethodOut)
def update_method(
    method_id: str,
    body: PaymentMethodUpdate,
    db: DbSession,
    user: AdminDependency,
) -> PaymentMethod:
    """Enable, disable, or rename a payment method (admin only)."""
    try:
        return update_payment_method(db, method_id, name=body.name, is_enabled=body.is_enabled)
    except PaymentMethodNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/shifts/{shift_id}/payment-totals", response_model=dict[str, int])
def shift_payment_totals(
    shift_id: int,
    db: DbSession,
    user: CurrentUserDependency,
) -> dict[str, int]:
    """Return the total collected per method for a shift's completed sales."""
    return payment_totals_by_method(db, shift_id)
