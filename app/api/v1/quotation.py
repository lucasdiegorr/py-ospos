from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep, DbSessionDep
from app.models.quotation import Quotation, QuotationLine
from app.schemas.quotation import (
    QuotationCreate,
    QuotationDetailResponse,
    QuotationLineCreate,
    QuotationResponse,
    QuotationUpdate,
)

router = APIRouter(prefix="/quotations", tags=["quotation"])


def calculate_line_total(
    quantity: float, unit_price: float, discount_percent: float, discount_amount: float
) -> float:
    subtotal = quantity * unit_price
    if discount_percent > 0:
        discount = subtotal * (discount_percent / 100)
    else:
        discount = discount_amount
    return subtotal - discount


async def recalculate_quotation_totals(db: AsyncSession, quotation: Quotation) -> None:
    subtotal = 0.0
    for line in quotation.lines:
        line.line_total = calculate_line_total(
            line.quantity, line.unit_price, line.discount_percent, line.discount_amount
        )
        subtotal += line.line_total

    quotation.subtotal = subtotal
    quotation.total = subtotal - quotation.discount_amount
    await db.flush()


@router.post("/", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    quotation_data: QuotationCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Quotation:
    expires_at = quotation_data.expires_at
    if expires_at is None:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    quotation = Quotation(
        status="draft",
        employee_id=current_user.id,
        customer_id=quotation_data.customer_id,
        expires_at=expires_at,
        comment=quotation_data.comment,
    )
    db.add(quotation)
    await db.flush()
    await db.refresh(quotation)
    return quotation


@router.get("/", response_model=list[QuotationDetailResponse])
async def list_quotations(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    status_filter: str | None = Query(None, description="Filter by status"),
    customer_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[Quotation]:
    query = select(Quotation)

    if status_filter:
        query = query.where(Quotation.status == status_filter)
    if customer_id:
        query = query.where(Quotation.customer_id == customer_id)

    query = query.offset(skip).limit(limit).order_by(Quotation.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{quotation_id}", response_model=QuotationDetailResponse)
async def get_quotation(
    quotation_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Quotation:
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()

    if quotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")

    return quotation


@router.post("/{quotation_id}/lines", response_model=QuotationDetailResponse, status_code=status.HTTP_201_CREATED)
async def add_quotation_line(
    quotation_id: str,
    line_data: QuotationLineCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Quotation:
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()

    if quotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")

    if quotation.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only add lines to draft quotations")

    line = QuotationLine(
        quotation_id=quotation_id,
        item_id=line_data.item_id,
        item_name=line_data.item_name,
        quantity=line_data.quantity,
        unit_price=line_data.unit_price,
        discount_percent=line_data.discount_percent,
        discount_amount=line_data.discount_amount,
    )
    line.line_total = calculate_line_total(
        line.quantity, line.unit_price, line.discount_percent, line.discount_amount
    )

    db.add(line)
    await db.flush()
    await db.refresh(quotation)

    return quotation


@router.patch("/{quotation_id}", response_model=QuotationDetailResponse)
async def update_quotation(
    quotation_id: str,
    quotation_data: QuotationUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Quotation:
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()

    if quotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")

    if quotation.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only update draft quotations")

    update_data = quotation_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quotation, field, value)

    await recalculate_quotation_totals(db, quotation)
    await db.refresh(quotation)

    return quotation


@router.delete("/{quotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quotation(
    quotation_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> None:
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()

    if quotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")

    if quotation.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only delete draft quotations")

    await db.delete(quotation)
    await db.flush()


@router.post("/{quotation_id}/send", response_model=QuotationResponse)
async def send_quotation(
    quotation_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Quotation:
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()

    if quotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")

    if quotation.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quotation already sent")

    if quotation.lines:
        await recalculate_quotation_totals(db, quotation)

    quotation.status = "sent"
    await db.flush()
    await db.refresh(quotation)

    return quotation