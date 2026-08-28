"""Sales service: atomic point-of-sale sale completion.

The cart is built client side; the server recomputes every line total from
the current prices (price-at-sale) and persists sale, items, payments, and an
optional delivery in a single transaction. Stock is decremented through the
inventory capability and payments go through the payments capability so the
fiado and coverage invariants stay in one place.

Offline flow: sale completion accepts an idempotency key; re-delivery of the
same key returns the existing sale. The sync capability dispatches
``sale.completed`` payloads here via ``register_operation``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.money import from_cents
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.product import Product
from app.models.sales import Sale, SaleItem
from app.services import inventory
from app.services.customers import CustomerNotFound
from app.services.payments import (
    FIADO,
    apply_fiado,
    record_payment,
    validate_payments_cover_total,
)
from app.services.sync import register_operation


class SaleError(Exception):
    """Base class for sale domain violations."""


class SaleNotFound(LookupError):
    """Raised when a sale does not exist."""


def complete_sale(
    db: Session,
    *,
    items: list[dict[str, Any]],
    payments: list[dict[str, Any]],
    customer_id: int | None = None,
    shift_id: int | None = None,
    delivery: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    actor_id: int | None = None,
) -> Sale:
    """Create a completed sale with its items, payments, stock, and delivery.

    Prices are taken from the product at completion time. The operation is
    atomic: any domain failure raises and leaves no partial sale.
    """
    if idempotency_key:
        existing = db.scalar(select(Sale).where(Sale.idempotency_key == idempotency_key))
        if existing is not None:
            return existing
    customer = _customer_or_404(db, customer_id)

    sale_items, total_cents = _build_items(db, items)
    sale = Sale(
        customer_id=customer_id,
        shift_id=shift_id,
        status="completed",
        total_cents=total_cents,
        idempotency_key=idempotency_key,
    )
    sale.items = sale_items
    db.add(sale)
    db.flush()

    for payment in payments:
        method = payment.get("method")
        amount_cents = payment.get("amount_cents", 0)
        if method == FIADO:
            apply_fiado(
                db,
                sale=sale,
                amount_cents=amount_cents,
                customer=customer,
            )
        else:
            record_payment(
                db,
                sale=sale,
                method=str(method),
                amount_cents=amount_cents,
                card_operator=payment.get("card_operator"),
                installments=payment.get("installments"),
            )
    validate_payments_cover_total(db, sale)

    for item in sale_items:
        product_id = item.product_id
        if product_id is None:
            raise SaleError("sale item references no product")
        base_units = item.quantity
        if item.pack:
            product = db.get(Product, product_id)
            pack_quantity = product.pack_quantity if product else None
            base_units = item.quantity * (pack_quantity or 0)
        inventory.consume_stock(
            db,
            product_id=product_id,
            quantity=base_units,
            actor_id=actor_id,
            commit=False,
        )

    if delivery is not None:
        db.add(Delivery(sale_id=sale.id, **delivery))

    db.commit()
    db.refresh(sale)
    return sale


def cancel_sale(db: Session, *, sale_id: int, reason: str, actor_id: int | None = None) -> Sale:
    """Cancel a completed sale: restore stock and reverse fiado balances."""
    if not reason.strip():
        raise SaleError("reason is required to cancel a sale")
    sale = _get_sale(db, sale_id)
    if sale.status != "completed":
        raise SaleError(f"Sale {sale_id} is already {sale.status}")
    for item in sale.items:
        product_id = item.product_id
        if product_id is None:
            raise SaleError("sale item references no product")
        inventory.restore_stock(
            db,
            product_id=product_id,
            quantity=item.quantity,
            as_pack=bool(item.pack),
            actor_id=actor_id,
            commit=False,
        )
    if sale.customer_id is not None:
        customer = db.get(Customer, sale.customer_id)
        if customer is not None:
            fiado_total = sum(
                payment.amount_cents for payment in sale.payments if payment.method == "fiado"
            )
            customer.outstanding_balance_cents = max(
                0, customer.outstanding_balance_cents - fiado_total
            )
    sale.status = "cancelled"
    sale.cancelled_reason = reason.strip()
    db.commit()
    db.refresh(sale)
    return sale


def get_sale(db: Session, sale_id: int) -> Sale:
    """Return a sale with items, payments, and delivery loaded."""
    return _get_sale(db, sale_id)


def search_sales(
    db: Session,
    *,
    customer_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
) -> list[Sale]:
    """Search sales by customer or creation-date range, newest first."""
    stmt = select(Sale).options(*_sale_detail_options())
    if customer_id is not None:
        stmt = stmt.where(Sale.customer_id == customer_id)
    if date_from is not None:
        stmt = stmt.where(Sale.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Sale.created_at <= date_to)
    stmt = stmt.order_by(Sale.created_at.desc()).limit(limit)
    return list(db.scalars(stmt))


def receipt_lines(db: Session, sale_id: int) -> list[str]:
    """Format a non-fiscal receipt for a completed sale."""
    sale = _get_sale(db, sale_id)
    lines = ["---------- RECEIPT ----------"]
    lines.append(f"Venda #{sale.id}")
    lines.append(sale.created_at.isoformat())
    lines.append("-" * 28)
    for item in sale.items:
        tag = "[PACK] " if item.pack else ""
        lines.append(f"{tag}{item.product_name}")
        lines.append(f"  {item.quantity} x {_money(item.unit_price_cents)}")
        lines.append(f"  = {_money(item.line_total_cents)}")
    lines.append(f"TOTAL: {_money(sale.total_cents)}")
    for payment in sale.payments:
        lines.append(f"{payment.method}: {_money(payment.amount_cents)}")
    lines.append(f"Status: {sale.status}")
    lines.append("-" * 28)
    return lines


def _build_items(db: Session, items: list[dict[str, Any]]) -> tuple[list[SaleItem], int]:
    """Price each line from the product's current price and sum the total."""
    if not items:
        raise SaleError("a sale must have at least one item")
    sale_items: list[SaleItem] = []
    total = 0
    for item in items:
        product_id = item.get("product_id")
        product = db.get(Product, product_id) if product_id else None
        if product is None:
            raise inventory.UnknownProductError(f"Unknown product: {product_id}")
        if not product.is_active:
            raise SaleError(f"Product '{product.name}' is inactive")
        quantity = item.get("quantity", 0)
        if not isinstance(quantity, int) or quantity <= 0:
            raise SaleError("item quantity must be a positive integer")
        pack = bool(item.get("pack", False))
        if pack:
            if not product.pack_quantity or product.pack_price_cents is None:
                raise SaleError(f"Product '{product.name}' has no pack definition")
            unit_price = product.pack_price_cents
        else:
            unit_price = product.unit_price_cents
        line_total = unit_price * quantity
        total += line_total
        sale_items.append(
            SaleItem(
                product_id=product.id,
                product_name=product.name,
                unit_price_cents=unit_price,
                quantity=quantity,
                pack=pack,
                line_total_cents=line_total,
            )
        )
    return sale_items, total


def _customer_or_404(db: Session, customer_id: int | None) -> Customer | None:
    if customer_id is None:
        return None
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise CustomerNotFound(f"customer {customer_id} not found")
    return customer


def _sale_detail_options():
    return [
        selectinload(Sale.items),
        selectinload(Sale.payments),
        selectinload(Sale.delivery),
    ]


def _get_sale(db: Session, sale_id: int) -> Sale:
    sale = db.scalar(select(Sale).options(*_sale_detail_options()).where(Sale.id == sale_id))
    if sale is None:
        raise SaleNotFound(f"Unknown sale: {sale_id}")
    return sale


def _money(cents: int) -> str:
    value = from_cents(cents)
    return f"R$ {value:.2f}"


def _apply_sale_completed(db: Session, payload: dict[str, Any]) -> None:
    """Sync handler for offline ``sale.completed`` payloads."""
    complete_sale(
        db,
        items=payload["items"],
        payments=payload["payments"],
        customer_id=payload.get("customer_id"),
        shift_id=payload.get("shift_id"),
        delivery=payload.get("delivery"),
        idempotency_key=payload.get("idempotency_key"),
        actor_id=payload.get("actor_id"),
    )


register_operation("sale.completed", _apply_sale_completed)
