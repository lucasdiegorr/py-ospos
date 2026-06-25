from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ExpenseCategory(BaseModel):
    __tablename__ = "expense_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Expense(BaseModel):
    __tablename__ = "expenses"

    category_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    employee_id: Mapped[str] = mapped_column(String(36))

    amount: Mapped[float] = mapped_column(default=0)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_recurring: Mapped[bool] = mapped_column(default=False)
    recurrence_pattern: Mapped[str | None] = mapped_column(String(20), nullable=True)

    deleted: Mapped[bool] = mapped_column(default=False)

    category: Mapped[ExpenseCategory | None] = relationship("ExpenseCategory")


class CashUp(BaseModel):
    __tablename__ = "cash_ups"

    employee_id: Mapped[str] = mapped_column(String(36))

    expected_cash: Mapped[float] = mapped_column(default=0)
    actual_cash: Mapped[float] = mapped_column(default=0)
    variance: Mapped[float] = mapped_column(default=0)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)