"""Product catalog service layer: categories and products.

Encapsulates the business rules of the products capability: unique SKUs,
category assignment, unit + pack pricing, and read-only availability computed
from the stock snapshot on the product. Stock mutations are owned by the
inventory capability; expiration is tracked per ``StockBatch`` there, so this
module never reads or writes product-level expiration.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Category, Product


def available_quantity(product: Product) -> int:
    """Total stock in base units: loose units plus units inside whole packs."""
    return (product.loose_units or 0) + (product.packs or 0) * (product.pack_quantity or 0)


def validate_pack(pack_quantity: int | None, pack_price_cents: int | None) -> None:
    """A pack is defined only when both quantity and price are provided."""
    if pack_quantity is None and pack_price_cents is None:
        return
    if pack_quantity is None or pack_price_cents is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="pack_quantity and pack_price_cents must be provided together",
        )
    if pack_quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="pack_quantity must be a positive integer",
        )
    if pack_price_cents < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="pack_price_cents must be non-negative",
        )


def _category_or_404(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )
    return category


def _product_or_404(db: Session, product_id: int) -> Product:
    product = db.scalar(
        select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found",
        )
    return product


# --- Categories -------------------------------------------------------------


def create_category(db: Session, name: str) -> Category:
    normalized = name.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="name must not be empty",
        )
    existing = db.scalar(select(Category).where(Category.name == normalized))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{normalized}' already exists",
        )
    category = Category(name=normalized)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def list_categories(db: Session) -> list[Category]:
    stmt = select(Category).options(selectinload(Category.products)).order_by(Category.name)
    return list(db.scalars(stmt))


def rename_category(db: Session, category_id: int, name: str) -> Category:
    category = _category_or_404(db, category_id)
    normalized = name.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="name must not be empty",
        )
    existing = db.scalar(
        select(Category).where(Category.name == normalized, Category.id != category_id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{normalized}' already exists",
        )
    category.name = normalized
    db.commit()
    db.refresh(category)
    return category


# --- Products ---------------------------------------------------------------


def create_product(
    db: Session,
    *,
    sku: str,
    name: str,
    category_id: int,
    unit_price_cents: int,
    cost_price_cents: int | None = None,
    pack_quantity: int | None = None,
    pack_price_cents: int | None = None,
    low_stock_threshold: int = 0,
) -> Product:
    sku = sku.strip()
    name = name.strip()
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="sku must not be empty",
        )
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="name must not be empty",
        )
    if unit_price_cents < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="unit_price_cents must be non-negative",
        )
    validate_pack(pack_quantity, pack_price_cents)
    _category_or_404(db, category_id)
    existing = db.scalar(select(Product).where(Product.sku == sku))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"SKU '{sku}' is already in use",
        )
    product = Product(
        sku=sku,
        name=name,
        category_id=category_id,
        unit_price_cents=unit_price_cents,
        cost_price_cents=cost_price_cents,
        pack_quantity=pack_quantity,
        pack_price_cents=pack_price_cents,
        low_stock_threshold=low_stock_threshold,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Product:
    return _product_or_404(db, product_id)


def list_products(
    db: Session,
    *,
    search: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
) -> list[Product]:
    stmt = select(Product).options(selectinload(Product.category))
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(term), Product.sku.ilike(term)))
    stmt = stmt.order_by(Product.name)
    return list(db.scalars(stmt))


def update_product(db: Session, product_id: int, updates: dict[str, Any]) -> Product:
    """Apply partial updates; values are validated by the API schema."""
    product = _product_or_404(db, product_id)

    if "name" in updates:
        name = updates["name"].strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="name must not be empty",
            )
        product.name = name
    if "sku" in updates:
        sku = updates["sku"].strip()
        if not sku:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="sku must not be empty",
            )
        existing = db.scalar(select(Product).where(Product.sku == sku, Product.id != product_id))
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"SKU '{sku}' is already in use",
            )
        product.sku = sku
    if "category_id" in updates:
        _category_or_404(db, updates["category_id"])
        product.category_id = updates["category_id"]
    if "unit_price_cents" in updates:
        if updates["unit_price_cents"] < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="unit_price_cents must be non-negative",
            )
        product.unit_price_cents = updates["unit_price_cents"]
    if "cost_price_cents" in updates:
        product.cost_price_cents = updates["cost_price_cents"]
    if "pack_quantity" in updates:
        product.pack_quantity = updates["pack_quantity"]
    if "pack_price_cents" in updates:
        product.pack_price_cents = updates["pack_price_cents"]
    if "low_stock_threshold" in updates:
        product.low_stock_threshold = updates["low_stock_threshold"]
    if "is_active" in updates:
        product.is_active = updates["is_active"]

    validate_pack(product.pack_quantity, product.pack_price_cents)
    db.commit()
    db.refresh(product)
    return product
