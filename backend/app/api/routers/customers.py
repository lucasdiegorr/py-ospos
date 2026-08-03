"""Customers capability router: registration, search, editing, fiado, history.

The module-level ``attendant_or_higher`` dependency is a handle to the RBAC
dependency produced by ``app.core.security.require_role``; keeping it at
module scope lets tests override it through ``app.dependency_overrides``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.schemas.customers import (
    CustomerCreate,
    CustomerHistoryOut,
    CustomerOut,
    CustomerUpdate,
    SaleOut,
)
from app.services import customers as service

router = APIRouter(prefix="/customers", tags=["customers"])

# ``require_role`` returns the raw dependency callable at runtime (its
# annotated return type is aspirational until the auth capability lands).
attendant_or_higher = cast(
    Callable[..., CurrentUser],
    require_role(Role.ATTENDANT, Role.MANAGER, Role.ADMIN),
)


def _not_found(customer_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"customer {customer_id} not found"
    )


def _to_out(customer: service.Customer) -> CustomerOut:
    return CustomerOut.model_validate(customer)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(attendant_or_higher)],
) -> CustomerOut:
    try:
        return _to_out(service.create_customer(db, data))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get("", response_model=list[CustomerOut])
def list_customers(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(attendant_or_higher)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[CustomerOut]:
    return [_to_out(customer) for customer in service.search_customers(db, q, limit=limit)]


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(attendant_or_higher)],
) -> CustomerOut:
    try:
        return _to_out(service.get_customer(db, customer_id))
    except service.CustomerNotFound as exc:
        raise _not_found(customer_id) from exc


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(attendant_or_higher)],
) -> CustomerOut:
    try:
        return _to_out(service.update_customer(db, customer_id, data))
    except service.CustomerNotFound as exc:
        raise _not_found(customer_id) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get("/{customer_id}/history", response_model=CustomerHistoryOut)
def get_customer_history(
    customer_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(attendant_or_higher)],
) -> CustomerHistoryOut:
    try:
        customer, sales = service.get_customer_history(db, customer_id)
    except service.CustomerNotFound as exc:
        raise _not_found(customer_id) from exc
    return CustomerHistoryOut(
        customer=_to_out(customer),
        outstanding_balance_cents=customer.outstanding_balance_cents,
        recent_sales=[SaleOut.model_validate(sale) for sale in sales],
    )
