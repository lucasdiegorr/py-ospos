"""Product categories API.

Categories are a lightweight taxonomy used to group products (beer, soft
drink, water, groceries). Management is restricted to manager/admin; listing
is open to attendants.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, cast

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator

from app.core.security import CurrentUser, Role, require_role
from app.db import Session, get_db
from app.models.product import Category
from app.services import products as service

router = APIRouter(prefix="/categories", tags=["categories"])

DB = Annotated[Session, Depends(get_db)]

# Stable dependency objects so tests can override them by identity. ``require_role``
# is typed for annotation position; cast to a callable for ``Depends(...)`` use.
manager_dep = cast(Callable[..., CurrentUser], require_role(Role.MANAGER, Role.ADMIN))
attendant_dep = cast(
    Callable[..., CurrentUser], require_role(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)
)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty or only whitespace")
        return value


class CategoryUpdate(CategoryCreate):
    pass


class CategoryRead(BaseModel):
    id: int
    name: str
    product_count: int = 0


def _to_read(category: Category) -> CategoryRead:
    return CategoryRead(
        id=category.id,
        name=category.name,
        product_count=len(category.products),
    )


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: DB,
    user: CurrentUser = Depends(attendant_dep),
) -> list[CategoryRead]:
    return [_to_read(category) for category in service.list_categories(db)]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: DB,
    user: CurrentUser = Depends(manager_dep),
) -> CategoryRead:
    return _to_read(service.create_category(db, payload.name))


@router.patch("/{category_id}", response_model=CategoryRead)
def rename_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DB,
    user: CurrentUser = Depends(manager_dep),
) -> CategoryRead:
    return _to_read(service.rename_category(db, category_id, payload.name))
