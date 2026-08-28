"""Inventory services: stock movements, pack break, and stock alerts.

Stock for a product is counted in base units on the product row
(``loose_units`` and whole ``packs``, each pack holding ``pack_quantity``
base units). ``StockBatch`` tracks dated stock in base units for expiration
tracking; ``StockMovement`` is the chronological log of every quantity delta
with actor. The sales capability calls ``consume_stock`` on sale completion;
automatic pack breaking is a transparent detail of that call.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.idempotency import utcnow
from app.models.inventory import StockBatch, StockMovement
from app.models.product import Product
from app.services.products import available_quantity


class InventoryError(Exception):
    """Base class for inventory domain violations."""


class InvalidQuantityError(InventoryError):
    """Raised when a quantity or delta is out of range."""


class InsufficientStockError(InventoryError):
    """Raised when a requested outflow exceeds the available quantity."""


class UnknownProductError(InventoryError):
    """Raised when referencing a product that does not exist."""


class ExpiringBatch(NamedTuple):
    """A dated stock batch within the expiring window, with its product."""

    product_id: int
    product_name: str
    quantity: int
    expiration_date: datetime | None
    expired: bool


def record_entry(
    db: Session,
    *,
    product_id: int,
    units: int = 0,
    packs: int = 0,
    expiration_date: datetime | None = None,
    actor_id: int | None = None,
) -> Product:
    """Record a manual stock entry: loose ``units`` and/or whole ``packs``.

    The received quantity is the base-unit total. Dated entries additionally
    create a ``StockBatch`` so the units participate in expiration tracking.
    """
    if units < 0 or packs < 0:
        raise InvalidQuantityError("units and packs must be non-negative")
    if units + packs == 0:
        raise InvalidQuantityError("entry must include units or packs")
    product = _product_or_404(db, product_id)
    base_units = 0
    if units > 0:
        product.loose_units += units
        base_units += units
    if packs > 0:
        pack_quantity = product.pack_quantity
        if not pack_quantity:
            raise InvalidQuantityError(f"Product {product_id} has no pack size")
        product.packs += packs
        base_units += packs * pack_quantity
    if expiration_date is not None:
        db.add(
            StockBatch(
                product_id=product_id,
                quantity=base_units,
                expiration_date=expiration_date,
            )
        )
    db.add(
        StockMovement(product_id=product_id, delta=base_units, reason="entry", actor_id=actor_id)
    )
    db.commit()
    db.refresh(product)
    return product


def consume_stock(
    db: Session,
    *,
    product_id: int,
    quantity: int,
    actor_id: int | None = None,
    reason: str = "sale",
    commit: bool = True,
) -> Product:
    """Sell or otherwise consume ``quantity`` base units of a product.

    Loose units are consumed first; when they run out, whole packs are broken
    (each break logged) and the requested units taken from the resulting loose
    stock. Dated batches are drained oldest-first so expiration tracking stays
    truthful. Refuses an outflow that exceeds the total available quantity.

    When ``commit=False`` the mutation stays pending so the caller (e.g. the
    sales capability) can persist several movements atomically.
    """
    if quantity <= 0:
        raise InvalidQuantityError("quantity must be positive")
    product = _product_or_404(db, product_id)
    if quantity > available_quantity(product):
        raise InsufficientStockError(
            f"Only {available_quantity(product)} units available, {quantity} requested"
        )
    remaining = quantity
    used_loose = min(product.loose_units or 0, remaining)
    product.loose_units -= used_loose
    remaining -= used_loose
    pack_quantity = product.pack_quantity or 0
    while remaining > 0 and product.packs > 0:
        product.packs -= 1
        product.loose_units += pack_quantity
        db.add(
            StockMovement(
                product_id=product_id,
                delta=pack_quantity,
                reason="break",
                actor_id=actor_id,
            )
        )
        step = min(remaining, pack_quantity)
        product.loose_units -= step
        remaining -= step
    if remaining > 0:
        raise InsufficientStockError("Insufficient total stock")
    _drain_batches(db, product_id, quantity)
    db.add(
        StockMovement(
            product_id=product_id,
            delta=-quantity,
            reason=reason,
            actor_id=actor_id,
        )
    )
    if commit:
        db.commit()
        db.refresh(product)
    return product


def restore_stock(
    db: Session,
    *,
    product_id: int,
    quantity: int,
    as_pack: bool = False,
    actor_id: int | None = None,
    commit: bool = True,
) -> Product:
    """Put stock back as loose units or whole packs (e.g. on sale cancel)."""
    if quantity <= 0:
        raise InvalidQuantityError("quantity must be positive")
    product = _product_or_404(db, product_id)
    if as_pack:
        if not product.pack_quantity:
            raise InvalidQuantityError(f"Product {product_id} has no pack size")
        product.packs += quantity
    else:
        product.loose_units += quantity
    db.add(
        StockMovement(
            product_id=product_id,
            delta=quantity,
            reason="cancel",
            actor_id=actor_id,
        )
    )
    if commit:
        db.commit()
        db.refresh(product)
    return product


def adjust_stock(
    db: Session,
    *,
    product_id: int,
    delta: int,
    reason: str,
    actor_id: int | None = None,
) -> Product:
    """Correct stock by ``delta`` base units, recorded with a reason.

    Positive deltas add loose units; negative deltas consume from loose units,
    breaking packs when needed, and may raise ``InsufficientStockError``.
    """
    if not reason.strip():
        raise InvalidQuantityError("reason must not be empty")
    if delta == 0:
        raise InvalidQuantityError("delta must be non-zero")
    if delta > 0:
        product = _product_or_404(db, product_id)
        product.loose_units += delta
        db.add(
            StockMovement(
                product_id=product_id, delta=delta, reason="adjustment", actor_id=actor_id
            )
        )
        db.commit()
        db.refresh(product)
        return product
    return consume_stock(
        db, product_id=product_id, quantity=-delta, reason="adjustment", actor_id=actor_id
    )


def get_product(db: Session, product_id: int) -> Product:
    return _product_or_404(db, product_id)


def list_movements(db: Session, product_id: int) -> list[StockMovement]:
    _product_or_404(db, product_id)
    stmt = (
        select(StockMovement)
        .where(StockMovement.product_id == product_id)
        .order_by(StockMovement.created_at, StockMovement.id)
    )
    return list(db.scalars(stmt))


def low_stock_products(db: Session) -> list[Product]:
    """Products at or below their configured low-stock threshold."""
    return [
        product
        for product in db.scalars(select(Product).order_by(Product.name))
        if available_quantity(product) <= product.low_stock_threshold
    ]


def expiring_stock(db: Session, *, window_days: int = 30) -> list[ExpiringBatch]:
    """Dated batches expiring within the window or already expired.

    Expiration is derived from the batch date (no separate flag); already
    expired batches are included with ``expired=True``.
    """
    cutoff = utcnow() + timedelta(days=window_days)
    rows = db.execute(
        select(StockBatch, Product.name)
        .join(Product, StockBatch.product_id == Product.id)
        .where(
            StockBatch.quantity > 0,
            StockBatch.expiration_date.is_not(None),
            StockBatch.expiration_date <= cutoff,
        )
        .order_by(StockBatch.expiration_date)
    ).all()
    now = utcnow()
    expiring: list[ExpiringBatch] = []
    for batch, name in rows:
        expiration = _utc(batch.expiration_date)
        if expiration is None:  # query filters expiration_date NOT NULL
            continue
        expiring.append(
            ExpiringBatch(
                product_id=batch.product_id,
                product_name=name,
                quantity=batch.quantity,
                expiration_date=expiration,
                expired=expiration < now,
            )
        )
    return expiring


def _utc(value: datetime | None) -> datetime | None:
    """Interpret a naive stored datetime as UTC (SQLite returns naive)."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _product_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise UnknownProductError(f"Unknown product: {product_id}")
    return product


def _drain_batches(db: Session, product_id: int, quantity: int) -> None:
    """Drain dated stock oldest-first, dropping exhausted batches."""
    batches = list(
        db.scalars(
            select(StockBatch)
            .where(StockBatch.product_id == product_id, StockBatch.quantity > 0)
            .order_by(StockBatch.expiration_date.is_(None), StockBatch.expiration_date)
        )
    )
    remaining = quantity
    for batch in batches:
        if remaining <= 0:
            break
        taken = min(batch.quantity, remaining)
        batch.quantity -= taken
        remaining -= taken
    for batch in batches:
        if batch.quantity == 0:
            db.delete(batch)
