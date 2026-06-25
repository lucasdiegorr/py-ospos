from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Invoice(BaseModel):
    __tablename__ = "invoices"

    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")

    employee_id: Mapped[str] = mapped_column(String(36))
    customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    subtotal: Mapped[float] = mapped_column(default=0)
    tax_amount: Mapped[float] = mapped_column(default=0)
    discount_amount: Mapped[float] = mapped_column(default=0)
    total: Mapped[float] = mapped_column(default=0)

    amount_paid: Mapped[float] = mapped_column(default=0)
    balance_due: Mapped[float] = mapped_column(default=0)

    due_date: Mapped[str | None] = mapped_column(String(36), nullable=True)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine", back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[list["InvoicePayment"]] = relationship(
        "InvoicePayment", back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(BaseModel):
    __tablename__ = "invoice_lines"

    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE")
    )

    item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255))

    quantity: Mapped[float] = mapped_column(default=1)
    unit_price: Mapped[float] = mapped_column(default=0)

    discount_percent: Mapped[float] = mapped_column(default=0)
    discount_amount: Mapped[float] = mapped_column(default=0)

    line_total: Mapped[float] = mapped_column(default=0)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="lines")


class InvoicePayment(BaseModel):
    __tablename__ = "invoice_payments"

    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE")
    )

    payment_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(default=0)
    payment_date: Mapped[str] = mapped_column(String(36))
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payments")


class CreditNote(BaseModel):
    __tablename__ = "credit_notes"

    credit_note_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    invoice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    amount: Mapped[float] = mapped_column(default=0)
    balance: Mapped[float] = mapped_column(default=0)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)