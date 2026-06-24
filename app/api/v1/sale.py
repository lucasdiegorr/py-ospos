from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep, DbSessionDep
from app.models.item import Item
from app.models.sale import Payment, Sale, SaleLine
from app.schemas.sale import (
    CartAddItemRequest,
    CartUpdateItemRequest,
    CompleteSaleRequest,
    PaymentCreate,
    SaleCreate,
    SaleResponse,
    SaleDetailResponse,
)

router = APIRouter(prefix="/sales", tags=["sale"])


def calculate_line_total(quantity: float, unit_price: float, discount_percent: float, discount_amount: float) -> float:
    subtotal = quantity * unit_price
    if discount_percent > 0:
        discount = subtotal * (discount_percent / 100)
    else:
        discount = discount_amount
    return subtotal - discount


async def recalculate_sale_totals(db: AsyncSession, sale: Sale) -> None:
    subtotal = 0.0
    for line in sale.lines:
        line.line_total = calculate_line_total(
            line.quantity, line.unit_price, line.discount_percent, line.discount_amount
        )
        subtotal += line.line_total

    sale.subtotal = subtotal
    sale.total = subtotal - sale.discount_amount + sale.tax_amount
    await db.flush()


@router.post("/cart", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_cart(
    sale_data: SaleCreate | None,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Sale:
    sale = Sale(
        status="open",
        employee_id=current_user.id,
        customer_id=sale_data.customer_id if sale_data else None,
    )
    db.add(sale)
    await db.flush()
    await db.refresh(sale)
    return sale


@router.get("/cart", response_model=SaleDetailResponse | None)
async def get_current_cart(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Sale | None:
    result = await db.execute(
        select(Sale)
        .where(Sale.employee_id == current_user.id, Sale.status == "open")
        .order_by(Sale.created_at.desc())
    )
    sale = result.scalar_one_or_none()

    if sale is None:
        return None

    return sale


@router.post("/cart/items", response_model=SaleDetailResponse)
async def add_item_to_cart(
    item_data: CartAddItemRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Sale:
    result = await db.execute(
        select(Sale)
        .where(Sale.employee_id == current_user.id, Sale.status == "open")
        .order_by(Sale.created_at.desc())
    )
    sale = result.scalar_one_or_none()

    if sale is None:
        sale = Sale(
            status="open",
            employee_id=current_user.id,
        )
        db.add(sale)
        await db.flush()

    if item_data.item_id:
        item_result = await db.execute(select(Item).where(Item.id == item_data.item_id))
        item = item_result.scalar_one_or_none()
        if item is None or item.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    line = SaleLine(
        sale_id=sale.id,
        item_id=item_data.item_id,
        item_name=item_data.item_name or (item.name if item_data.item_id else "Unknown"),
        quantity=item_data.quantity,
        unit_price=item_data.unit_price if item_data.unit_price > 0 else (item.unit_price if item_data.item_id else 0),
        cost_price=item.cost_price if item_data.item_id else 0,
        discount_percent=item_data.discount_percent,
    )
    line.line_total = calculate_line_total(
        line.quantity, line.unit_price, line.discount_percent, line.discount_amount
    )

    db.add(line)
    await db.flush()
    await db.refresh(sale)

    return sale


@router.patch("/cart/items", response_model=SaleDetailResponse)
async def update_cart_item(
    update_data: CartUpdateItemRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Sale:
    result = await db.execute(
        select(Sale)
        .where(Sale.employee_id == current_user.id, Sale.status == "open")
        .order_by(Sale.created_at.desc())
    )
    sale = result.scalar_one_or_none()

    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active cart found")

    line_result = await db.execute(select(SaleLine).where(SaleLine.id == update_data.line_id, SaleLine.sale_id == sale.id))
    line = line_result.scalar_one_or_none()

    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found")

    if update_data.quantity is not None:
        line.quantity = update_data.quantity
    if update_data.discount_percent is not None:
        line.discount_percent = update_data.discount_percent
    if update_data.discount_amount is not None:
        line.discount_amount = update_data.discount_amount

    line.line_total = calculate_line_total(
        line.quantity, line.unit_price, line.discount_percent, line.discount_amount
    )

    await recalculate_sale_totals(db, sale)

    return sale


@router.delete("/cart/items/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(
    line_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> None:
    result = await db.execute(
        select(Sale)
        .where(Sale.employee_id == current_user.id, Sale.status == "open")
        .order_by(Sale.created_at.desc())
    )
    sale = result.scalar_one_or_none()

    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active cart found")

    line_result = await db.execute(select(SaleLine).where(SaleLine.id == line_id, SaleLine.sale_id == sale.id))
    line = line_result.scalar_one_or_none()

    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found")

    await db.delete(line)
    await db.flush()
    await recalculate_sale_totals(db, sale)


@router.post("/cart/complete", response_model=SaleDetailResponse)
async def complete_sale(
    complete_data: CompleteSaleRequest,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Sale:
    result = await db.execute(
        select(Sale)
        .where(Sale.employee_id == current_user.id, Sale.status == "open")
        .order_by(Sale.created_at.desc())
    )
    sale = result.scalar_one_or_none()

    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active cart found")

    if len(sale.lines) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot complete empty sale")

    total_payment = sum(p.amount for p in complete_data.payments)
    if total_payment < sale.total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient payment")

    for payment_data in complete_data.payments:
        payment = Payment(
            sale_id=sale.id,
            payment_type=payment_data.payment_type,
            amount=payment_data.amount,
            reference_number=payment_data.reference_number,
        )
        db.add(payment)

    sale.status = "completed"
    sale.completed_at = datetime.utcnow().isoformat()
    if complete_data.customer_id:
        sale.customer_id = complete_data.customer_id
    if complete_data.comment:
        sale.comment = complete_data.comment

    await db.flush()
    await db.refresh(sale)

    return sale


@router.post("/cart/suspend", response_model=SaleResponse)
async def suspend_cart(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Sale:
    result = await db.execute(
        select(Sale)
        .where(Sale.employee_id == current_user.id, Sale.status == "open")
        .order_by(Sale.created_at.desc())
    )
    sale = result.scalar_one_or_none()

    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active cart found")

    sale.status = "suspended"
    sale.suspended_at = datetime.utcnow().isoformat()

    await db.flush()
    await db.refresh(sale)

    return sale


@router.get("/suspended", response_model=list[SaleDetailResponse])
async def list_suspended_sales(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[Sale]:
    result = await db.execute(
        select(Sale)
        .where(Sale.employee_id == current_user.id, Sale.status == "suspended")
        .order_by(Sale.suspended_at.desc())
    )
    return list(result.scalars().all())


@router.post("/suspended/{sale_id}/recall", response_model=SaleDetailResponse)
async def recall_sale(
    sale_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Sale:
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id, Sale.employee_id == current_user.id, Sale.status == "suspended")
    )
    sale = result.scalar_one_or_none()

    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suspended sale not found")

    existing_cart = await db.execute(
        select(Sale)
        .where(Sale.employee_id == current_user.id, Sale.status == "open")
    )
    existing = existing_cart.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot recall while cart is active. Complete or suspend current cart first.",
        )

    sale.status = "open"
    sale.suspended_at = None

    await db.flush()
    await db.refresh(sale)

    return sale


@router.post("/{sale_id}/void", response_model=SaleResponse)
async def void_sale(
    sale_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Sale:
    result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.employee_id == current_user.id)
    )
    sale = result.scalar_one_or_none()

    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")

    if sale.status == "voided":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sale already voided")

    if sale.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot void completed sale. Use return instead.",
        )

    sale.status = "voided"
    await db.flush()
    await db.refresh(sale)

    return sale