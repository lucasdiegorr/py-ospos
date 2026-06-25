from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Quotation(BaseModel):
    __tablename__ = "quotations"

    status: Mapped[str] = mapped_column(String(20), default="draft")

    employee_id: Mapped[str] = mapped_column(String(36))
    customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    expires_at: Mapped[str | None] = mapped_column(String(36), nullable=True)

    subtotal: Mapped[float] = mapped_column(default=0)
    discount_amount: Mapped[float] = mapped_column(default=0)
    total: Mapped[float] = mapped_column(default=0)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list["QuotationLine"]] = relationship(
        "QuotationLine", back_populates="quotation", cascade="all, delete-orphan"
    )


class QuotationLine(BaseModel):
    __tablename__ = "quotation_lines"

    quotation_id: Mapped[str] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE")
    )

    item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    item_name: Mapped[str] = mapped_column(String(255))

    quantity: Mapped[float] = mapped_column(default=1)
    unit_price: Mapped[float] = mapped_column(default=0)

    discount_percent: Mapped[float] = mapped_column(default=0)
    discount_amount: Mapped[float] = mapped_column(default=0)

    line_total: Mapped[float] = mapped_column(default=0)

    quotation: Mapped[Quotation] = relationship("Quotation", back_populates="lines")