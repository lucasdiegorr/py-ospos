from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep, DbSessionDep
from app.models.invoice import CreditNote, Invoice, InvoiceLine, InvoicePayment
from app.schemas.invoice import (
    CreditNoteCreate,
    CreditNoteResponse,
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoicePaymentCreate,
    InvoiceResponse,
    InvoiceUpdate,
)

router = APIRouter(prefix="/invoices", tags=["invoice"])

COUNTER = {"invoice": 1000, "credit_note": 500}


def generate_invoice_number() -> str:
    COUNTER["invoice"] += 1
    return f"INV-{COUNTER['invoice']:04d}"


def calculate_line_total(
    quantity: float, unit_price: float, discount_percent: float, discount_amount: float
) -> float:
    subtotal = quantity * unit_price
    if discount_percent > 0:
        discount = subtotal * (discount_percent / 100)
    else:
        discount = discount_amount
    return subtotal - discount


async def recalculate_invoice_totals(db: AsyncSession, invoice: Invoice) -> None:
    subtotal = sum(
        calculate_line_total(line.quantity, line.unit_price, line.discount_percent, line.discount_amount)
        for line in invoice.lines
    )
    invoice.subtotal = subtotal
    invoice.total = subtotal - invoice.discount_amount + invoice.tax_amount
    invoice.balance_due = invoice.total - invoice.amount_paid
    await db.flush()


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Invoice:
    invoice = Invoice(
        invoice_number=generate_invoice_number(),
        status="draft",
        employee_id=current_user.id,
        customer_id=invoice_data.customer_id,
        due_date=invoice_data.due_date or (datetime.utcnow() + timedelta(days=30)).isoformat(),
        comment=invoice_data.comment,
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)
    return invoice


@router.get("/", response_model=list[InvoiceDetailResponse])
async def list_invoices(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    status_filter: str | None = Query(None),
    customer_id: str | None = None,
    overdue: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[Invoice]:
    query = select(Invoice)

    if status_filter:
        query = query.where(Invoice.status == status_filter)
    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)
    if overdue:
        query = query.where(Invoice.status == "sent", Invoice.balance_due > 0)

    query = query.offset(skip).limit(limit).order_by(Invoice.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
async def get_invoice(
    invoice_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.post("/{invoice_id}/lines", response_model=InvoiceDetailResponse, status_code=status.HTTP_201_CREATED)
async def add_invoice_line(
    invoice_id: str,
    line_data: dict,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only add lines to draft invoices")

    line = InvoiceLine(
        invoice_id=invoice_id,
        item_id=line_data.get("item_id"),
        item_name=line_data.get("item_name", ""),
        quantity=line_data.get("quantity", 1),
        unit_price=line_data.get("unit_price", 0),
        discount_percent=line_data.get("discount_percent", 0),
        discount_amount=line_data.get("discount_amount", 0),
    )
    line.line_total = calculate_line_total(
        line.quantity, line.unit_price, line.discount_percent, line.discount_amount
    )
    db.add(line)
    await db.flush()
    await recalculate_invoice_totals(db, invoice)
    await db.refresh(invoice)
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceDetailResponse)
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    update_data = invoice_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)

    await recalculate_invoice_totals(db, invoice)
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/payments", response_model=InvoiceDetailResponse, status_code=status.HTTP_201_CREATED)
async def add_invoice_payment(
    invoice_id: str,
    payment_data: InvoicePaymentCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    if invoice.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice already paid")
    if invoice.status == "voided":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add payment to voided invoice")

    payment = InvoicePayment(
        invoice_id=invoice_id,
        payment_type=payment_data.payment_type,
        amount=payment_data.amount,
        payment_date=payment_data.payment_date or datetime.utcnow().isoformat(),
        reference_number=payment_data.reference_number,
    )
    db.add(payment)

    invoice.amount_paid += payment_data.amount
    invoice.balance_due = invoice.total - invoice.amount_paid

    if invoice.balance_due <= 0:
        invoice.status = "paid"
        invoice.balance_due = 0

    await db.flush()
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    if invoice.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice already sent")

    if not invoice.lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot send invoice without lines")

    invoice.status = "sent"
    await db.flush()
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/void", response_model=InvoiceResponse)
async def void_invoice(
    invoice_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Invoice:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    if invoice.status == "voided":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice already voided")

    invoice.status = "voided"
    await db.flush()
    await db.refresh(invoice)
    return invoice


@router.post("/credit-notes", response_model=CreditNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_credit_note(
    credit_note_data: CreditNoteCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> CreditNote:
    COUNTER["credit_note"] += 1
    credit_note = CreditNote(
        credit_note_number=f"CN-{COUNTER['credit_note']:04d}",
        invoice_id=credit_note_data.invoice_id,
        customer_id=credit_note_data.customer_id,
        amount=credit_note_data.amount,
        balance=credit_note_data.amount,
        reason=credit_note_data.reason,
    )
    db.add(credit_note)
    await db.flush()
    await db.refresh(credit_note)
    return credit_note