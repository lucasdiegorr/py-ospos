"""Inventory capability router: stock entry, adjustment, alerts, and log.

Stock entry and adjustment are manager/admin operations; stock queries,
movement history, low-stock and expiring lists are open to attendants (who
need stock visibility at the point of sale, per the users spec).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.models.inventory import StockMovement
from app.models.product import Product
from app.services import inventory as service
from app.services.inventory import (
    ExpiringBatch,
    InsufficientStockError,
    InvalidQuantityError,
    UnknownProductError,
)
from app.services.products import available_quantity

router = APIRouter(prefix="/inventory", tags=["inventory"])

DbSession = Annotated[Session, Depends(get_db)]


def _role_dependency(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a role-checked current-user dependency (typed for ``Depends``)."""
    return cast(Callable[..., CurrentUser], require_role(*roles))


attendant_or_higher = _role_dependency(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)
manager_or_higher = _role_dependency(Role.MANAGER, Role.ADMIN)

AttendantDependency = Annotated[CurrentUser, Depends(attendant_or_higher)]
ManagerDependency = Annotated[CurrentUser, Depends(manager_or_higher)]


class EntryCreate(BaseModel):
    """A manual stock entry in loose units and/or whole packs."""

    units: int = Field(default=0, ge=0)
    packs: int = Field(default=0, ge=0)
    expiration_date: datetime | None = None

    @model_validator(mode="after")
    def _entry_positive(self) -> EntryCreate:
        if self.units + self.packs == 0:
            raise ValueError("entry must include units or packs")
        return self


class AdjustmentBody(BaseModel):
    """A stock adjustment (correction) with its reason."""

    delta: int
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be empty")
        return value


class StockOut(BaseModel):
    """A product's stock view, always expressed in base units."""

    id: int
    sku: str
    name: str
    loose_units: int
    packs: int
    pack_quantity: int | None
    low_stock_threshold: int
    available_quantity: int
    low_stock: bool


class LowStockOut(BaseModel):
    id: int
    sku: str
    name: str
    available_quantity: int
    low_stock_threshold: int


class MovementOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    product_id: int
    delta: int
    reason: str
    actor_id: int | None
    created_at: datetime


class ExpiringOut(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    expiration_date: datetime
    expired: bool


def _stock_out(product: Product) -> StockOut:
    quantity = available_quantity(product)
    return StockOut(
        id=product.id,
        sku=product.sku,
        name=product.name,
        loose_units=product.loose_units or 0,
        packs=product.packs or 0,
        pack_quantity=product.pack_quantity,
        low_stock_threshold=product.low_stock_threshold,
        available_quantity=quantity,
        low_stock=quantity <= product.low_stock_threshold,
    )


@router.post("/products/{product_id}/entry", response_model=StockOut)
def record_entry(
    product_id: int,
    body: EntryCreate,
    db: DbSession,
    user: ManagerDependency,
) -> StockOut:
    """Record a manual stock entry (manager or admin)."""
    try:
        product = service.record_entry(
            db,
            product_id=product_id,
            units=body.units,
            packs=body.packs,
            expiration_date=body.expiration_date,
            actor_id=user.user_id,
        )
    except UnknownProductError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidQuantityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return _stock_out(product)


@router.post("/products/{product_id}/adjust", response_model=StockOut)
def adjust(
    product_id: int,
    body: AdjustmentBody,
    db: DbSession,
    user: ManagerDependency,
) -> StockOut:
    """Adjust a product's stock with a reason (manager or admin)."""
    try:
        product = service.adjust_stock(
            db,
            product_id=product_id,
            delta=body.delta,
            reason=body.reason,
            actor_id=user.user_id,
        )
    except UnknownProductError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidQuantityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except InsufficientStockError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _stock_out(product)


@router.get("/products/{product_id}/stock", response_model=StockOut)
def stock(product_id: int, db: DbSession, user: AttendantDependency) -> StockOut:
    """Current stock view for a product in base units (any authenticated user)."""
    try:
        return _stock_out(service.get_product(db, product_id))
    except UnknownProductError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/products/{product_id}/movements", response_model=list[MovementOut])
def movements(product_id: int, db: DbSession, user: AttendantDependency) -> list[StockMovement]:
    """Chronological movement log for a product (any authenticated user)."""
    try:
        return service.list_movements(db, product_id)
    except UnknownProductError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/low-stock", response_model=list[LowStockOut])
def low_stock(db: DbSession, user: AttendantDependency) -> list[LowStockOut]:
    """Products at or below their low-stock threshold."""
    return [
        LowStockOut(
            id=p.id,
            sku=p.sku,
            name=p.name,
            available_quantity=available_quantity(p),
            low_stock_threshold=p.low_stock_threshold,
        )
        for p in service.low_stock_products(db)
    ]


@router.get("/expiring", response_model=list[ExpiringOut])
def expiring(
    db: DbSession,
    user: AttendantDependency,
    window_days: int = Query(default=30, ge=1, le=365),
) -> list[ExpiringBatch]:
    """Dated stock expiring within the window or already expired."""
    return service.expiring_stock(db, window_days=window_days)
