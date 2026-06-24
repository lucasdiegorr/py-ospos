from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Sale(BaseModel):
    __tablename__ = "sales"

    status: Mapped[str] = mapped_column(String(20), default="open")

    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"))
    customer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("customers.id"), nullable=True)

    subtotal: Mapped[float] = mapped_column(default=0)
    tax_amount: Mapped[float] = mapped_column(default=0)
    discount_amount: Mapped[float] = mapped_column(default=0)
    total: Mapped[float] = mapped_column(default=0)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    completed_at: Mapped[str | None] = mapped_column(String(36), nullable=True)
    suspended_at: Mapped[str | None] = mapped_column(String(36), nullable=True)

    lines: Mapped[list["SaleLine"]] = relationship("SaleLine", back_populates="sale", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="sale", cascade="all, delete-orphan")


class SaleLine(BaseModel):
    __tablename__ = "sale_lines"

    sale_id: Mapped[str] = mapped_column(String(36), ForeignKey("sales.id", ondelete="CASCADE"))

    item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("items.id"), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255))

    quantity: Mapped[float] = mapped_column(default=1)
    unit_price: Mapped[float] = mapped_column(default=0)
    cost_price: Mapped[float] = mapped_column(default=0)

    discount_percent: Mapped[float] = mapped_column(default=0)
    discount_amount: Mapped[float] = mapped_column(default=0)

    line_total: Mapped[float] = mapped_column(default=0)

    sale: Mapped[Sale] = relationship("Sale", back_populates="lines")


class Payment(BaseModel):
    __tablename__ = "payments"

    sale_id: Mapped[str] = mapped_column(String(36), ForeignKey("sales.id", ondelete="CASCADE"))

    payment_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(default=0)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    sale: Mapped[Sale] = relationship("Sale", back_populates="payments")