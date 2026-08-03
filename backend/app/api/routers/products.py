"""Product catalog API: product endpoints.

Management (create/edit) is restricted to manager/admin; search and listing is
open to attendants. Expiration is tracked by the inventory capability
(``StockBatch``), so products here never carry an expiration attribute.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.security import CurrentUser, Role, require_role
from app.db import Session, get_db
from app.models.product import Product
from app.services import products as service

router = APIRouter(prefix="/products", tags=["products"])

DB = Annotated[Session, Depends(get_db)]

# Stable dependency objects so tests can override them by identity. ``require_role``
# is typed for annotation position; cast to a callable for ``Depends(...)`` use.
manager_dep = cast(Callable[..., CurrentUser], require_role(Role.MANAGER, Role.ADMIN))
attendant_dep = cast(
    Callable[..., CurrentUser], require_role(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)
)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=50)
    category_id: int
    unit_price_cents: int = Field(ge=0)
    cost_price_cents: int | None = Field(default=None, ge=0)
    pack_quantity: int | None = Field(default=None, ge=1)
    pack_price_cents: int | None = Field(default=None, ge=0)
    low_stock_threshold: int = Field(default=0, ge=0)

    @field_validator("name", "sku")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty or only whitespace")
        return value

    @model_validator(mode="after")
    def _pack_definition(self) -> ProductCreate:
        if (self.pack_quantity is None) != (self.pack_price_cents is None):
            raise ValueError("pack_quantity and pack_price_cents must be provided together")
        return self


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    category_id: int | None = None
    unit_price_cents: int | None = Field(default=None, ge=0)
    cost_price_cents: int | None = Field(default=None, ge=0)
    pack_quantity: int | None = Field(default=None, ge=1)
    pack_price_cents: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("name", "sku")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("must not be empty or only whitespace")
        return value

    @model_validator(mode="after")
    def _pack_definition(self) -> ProductUpdate:
        if (self.pack_quantity is None) != (self.pack_price_cents is None):
            raise ValueError("pack_quantity and pack_price_cents must be provided together")
        return self


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    category_id: int
    category_name: str | None = None
    unit_price_cents: int
    cost_price_cents: int | None = None
    pack_quantity: int | None = None
    pack_price_cents: int | None = None
    loose_units: int = 0
    packs: int = 0
    low_stock_threshold: int = 0
    is_active: bool = True
    available_quantity: int


def _to_read(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category_id=product.category_id,
        category_name=product.category.name if product.category else None,
        unit_price_cents=product.unit_price_cents,
        cost_price_cents=product.cost_price_cents,
        pack_quantity=product.pack_quantity,
        pack_price_cents=product.pack_price_cents,
        loose_units=product.loose_units,
        packs=product.packs,
        low_stock_threshold=product.low_stock_threshold,
        is_active=product.is_active,
        available_quantity=service.available_quantity(product),
    )


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: DB,
    user: CurrentUser = Depends(manager_dep),
) -> ProductRead:
    product = service.create_product(
        db,
        sku=payload.sku,
        name=payload.name,
        category_id=payload.category_id,
        unit_price_cents=payload.unit_price_cents,
        cost_price_cents=payload.cost_price_cents,
        pack_quantity=payload.pack_quantity,
        pack_price_cents=payload.pack_price_cents,
        low_stock_threshold=payload.low_stock_threshold,
    )
    return _to_read(product)


@router.get("", response_model=list[ProductRead])
def list_products(
    db: DB,
    user: CurrentUser = Depends(attendant_dep),
    search: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
) -> list[ProductRead]:
    if include_inactive and user.role not in (Role.MANAGER, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and admins can list inactive products",
        )
    products = service.list_products(
        db,
        search=search,
        category_id=category_id,
        include_inactive=include_inactive,
    )
    return [_to_read(product) for product in products]


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    db: DB,
    user: CurrentUser = Depends(attendant_dep),
) -> ProductRead:
    return _to_read(service.get_product(db, product_id))


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: DB,
    user: CurrentUser = Depends(manager_dep),
) -> ProductRead:
    updates = payload.model_dump(exclude_unset=True)
    product = service.update_product(db, product_id, updates)
    return _to_read(product)
