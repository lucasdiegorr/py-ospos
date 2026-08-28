"""Reporting services.

Reports are computed from the server's known data only and are manager/admin
only. The pending-sync count is exposed through the sync capability, which
also surfaces server-side entries awaiting reconciliation (the client's own
outbox count is the client's concern at render time).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cash_register import CashMovement
from app.models.customer import Customer
from app.models.product import Product
from app.models.sales import Payment, Sale, SaleItem
from app.services import inventory, sync

VALID_PERIODS = ("day", "week", "month")


class ReportingError(Exception):
    """Base class for reporting domain violations."""


class InvalidPeriodError(ReportingError):
    """Raised when an unknown grouping period is requested."""


class InvalidRangeError(ReportingError):
    """Raised when a date range is inverted."""


def sales_by_period(
    db: Session,
    *,
    period: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Total revenue, sale count, and average ticket grouped by bucket.

    Buckets are day, ISO week (starting Monday), or calendar month, over the
    optional date range. The sale count excludes cancelled sales.
    """
    _validate_range(date_from, date_to)
    rows = _completed_sales(db, date_from, date_to)
    buckets: dict[str, list[int]] = {}
    for created_at, total in rows:
        key = _bucket_key(date=_as_date(created_at), period=period)
        buckets.setdefault(key, []).append(int(total))
    result = []
    for key in sorted(buckets):
        sale_totals = buckets[key]
        count = len(sale_totals)
        total = sum(sale_totals)
        result.append(
            {
                "period": key,
                "total_cents": total,
                "sale_count": count,
                "avg_cents": round(total / count) if count else 0,
            }
        )
    return result


def best_sellers(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 10,
) -> list[dict]:
    """Top products by units sold, with quantity and revenue."""
    _validate_range(date_from, date_to)
    stmt = (
        select(
            SaleItem.product_id,
            SaleItem.product_name,
            func.sum(SaleItem.quantity),
            func.sum(SaleItem.line_total_cents),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .where(Sale.status == "completed")
    )
    if date_from is not None:
        stmt = stmt.where(Sale.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Sale.created_at <= date_to)
    stmt = (
        stmt.group_by(SaleItem.product_id, SaleItem.product_name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(limit)
    )
    return [
        {
            "product_id": product_id,
            "product_name": name,
            "quantity": int(quantity or 0),
            "revenue_cents": int(revenue or 0),
        }
        for product_id, name, quantity, revenue in db.execute(stmt)
    ]


def critical_stock(db: Session, *, window_days: int = 30) -> dict:
    """Low-stock products plus dated stock expiring within the window."""
    low_stock = [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "available_quantity": inventory.available_quantity(p),
            "low_stock_threshold": p.low_stock_threshold,
        }
        for p in inventory.low_stock_products(db)
    ]
    expiring = [
        {
            "product_id": batch.product_id,
            "product_name": batch.product_name,
            "quantity": batch.quantity,
            "expiration_date": batch.expiration_date,
            "expired": batch.expired,
        }
        for batch in inventory.expiring_stock(db, window_days=window_days)
    ]
    return {"low_stock": low_stock, "expiring": expiring}


def open_fiados(db: Session) -> list[dict]:
    """Customers with outstanding balances, oldest debt, and total owed."""
    customers = list(db.scalars(select(Customer).where(Customer.outstanding_balance_cents > 0)))
    oldest = {
        customer_id: oldest_at
        for customer_id, oldest_at in db.execute(
            select(Sale.customer_id, func.min(Sale.created_at))
            .join(Payment, Sale.id == Payment.sale_id)
            .where(
                Sale.status == "completed",
                Payment.method == "fiado",
                Sale.customer_id.is_not(None),
            )
            .group_by(Sale.customer_id)
        ).all()
    }
    return [
        {
            "customer_id": customer.id,
            "name": customer.name,
            "outstanding_balance_cents": customer.outstanding_balance_cents,
            "oldest_debt_at": oldest.get(customer.id),
        }
        for customer in customers
    ]


def cash_flow(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Daily money in (sales + supplies) and out (bleeds), with a net balance."""
    _validate_range(date_from, date_to)
    sales_stmt = select(Sale.created_at, Sale.total_cents).where(Sale.status == "completed")
    if date_from is not None:
        sales_stmt = sales_stmt.where(Sale.created_at >= date_from)
    if date_to is not None:
        sales_stmt = sales_stmt.where(Sale.created_at <= date_to)
    rows: dict[str, dict] = {}
    for created_at, total in db.execute(sales_stmt):
        day = _day_key(created_at)
        bucket = rows.setdefault(day, {"sales": 0})
        bucket["sales"] = bucket.get("sales", 0) + int(total)
    movements_stmt = select(CashMovement.created_at, CashMovement.type, CashMovement.amount_cents)
    if date_from is not None:
        movements_stmt = movements_stmt.where(CashMovement.created_at >= date_from)
    if date_to is not None:
        movements_stmt = movements_stmt.where(CashMovement.created_at <= date_to)
    for created_at, type, amount in db.execute(movements_stmt):
        day = _day_key(created_at)
        bucket = rows.setdefault(day, {"sales": 0})
        bucket[type] = bucket.get(type, 0) + int(amount)
    result = []
    for day in sorted(rows):
        bucket = rows[day]
        sales = bucket.get("sales", 0)
        supplies = bucket.get("supply", 0)
        bleeds = bucket.get("bleed", 0)
        money_in = sales + supplies
        money_out = bleeds
        result.append(
            {
                "day": day,
                "sales_cents": sales,
                "supplies_cents": supplies,
                "bleeds_cents": bleeds,
                "in_cents": money_in,
                "out_cents": money_out,
                "net_cents": money_in - money_out,
            }
        )
    return result


def margin_by_product(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Per-product revenue and, when a cost price is recorded, the margin."""
    _validate_range(date_from, date_to)
    stmt = (
        select(
            SaleItem.product_id,
            SaleItem.product_name,
            Product.cost_price_cents,
            func.sum(SaleItem.quantity),
            func.sum(SaleItem.line_total_cents),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .join(Product, SaleItem.product_id == Product.id)
        .where(Sale.status == "completed")
    )
    if date_from is not None:
        stmt = stmt.where(Sale.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Sale.created_at <= date_to)
    stmt = stmt.group_by(SaleItem.product_id, SaleItem.product_name, Product.cost_price_cents)
    result = []
    for product_id, name, cost_cents, quantity, revenue in db.execute(stmt):
        revenue = int(revenue or 0)
        quantity = int(quantity or 0)
        margin: int | None = None
        margin_pct: float | None = None
        if cost_cents is not None:
            margin = revenue - int(cost_cents) * quantity
            margin_pct = round(margin / revenue * 100, 2) if revenue else None
        result.append(
            {
                "product_id": product_id,
                "product_name": name,
                "quantity": quantity,
                "revenue_cents": revenue,
                "cost_cents": int(cost_cents) if cost_cents is not None else None,
                "margin_cents": margin,
                "margin_pct": margin_pct,
            }
        )
    return result


def pending_sync_count(db: Session) -> int:
    """Server-side count of writes the system has yet to settle."""
    return sync.pending_sync_count(db)


def _completed_sales(
    db: Session, date_from: datetime | None, date_to: datetime | None
) -> list[tuple[datetime, int]]:
    stmt = select(Sale.created_at, Sale.total_cents).where(Sale.status == "completed")
    if date_from is not None:
        stmt = stmt.where(Sale.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Sale.created_at <= date_to)
    return [(created_at, int(total)) for created_at, total in db.execute(stmt)]


def _bucket_key(*, date: date, period: str) -> str:
    if period == "day":
        return date.isoformat()
    if period == "week":
        return (date - timedelta(days=date.weekday())).isoformat()
    if period == "month":
        return date.strftime("%Y-%m")
    raise InvalidPeriodError(f"Invalid period: {period} (expected day, week, or month)")


def _day_key(dt: datetime) -> str:
    return _as_date(dt).isoformat()


def _as_date(dt: datetime) -> date:
    """Extract the date from a possibly-naive stored timestamp (UTC)."""
    if dt.tzinfo is not None:
        return dt.astimezone().date()
    return dt.date()


def _validate_range(date_from: datetime | None, date_to: datetime | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidRangeError("date_from must not be after date_to")
