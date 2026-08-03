"""Product catalog models: categories and products.

A product has a base unit price plus an optional pack (fixed quantity of base
units with its own price). Stock is tracked in base units: ``loose_units``
plus ``packs`` (each pack holds ``pack_quantity`` base units). Expiration is
tracked per batch in the inventory model, not here.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.domain.idempotency import utcnow


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Packaging: base unit (always) + optional pack.
    pack_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pack_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Stock in base units.
    loose_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    packs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    category: Mapped[Category] = relationship(back_populates="products")
