from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep, DbSessionDep
from app.models.expense import CashUp, Expense, ExpenseCategory
from app.schemas.expense import (
    CashUpCreate,
    CashUpResponse,
    ExpenseCategoryCreate,
    ExpenseCategoryResponse,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)

router = APIRouter(prefix="/expenses", tags=["expense"])


@router.post("/categories", response_model=ExpenseCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_expense_category(
    category_data: ExpenseCategoryCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> ExpenseCategory:
    category = ExpenseCategory(**category_data.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@router.get("/categories", response_model=list[ExpenseCategoryResponse])
async def list_expense_categories(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[ExpenseCategory]:
    result = await db.execute(select(ExpenseCategory))
    return list(result.scalars().all())


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Expense:
    expense = Expense(
        employee_id=current_user.id,
        category_id=expense_data.category_id,
        amount=expense_data.amount,
        description=expense_data.description,
        reference_number=expense_data.reference_number,
        is_recurring=expense_data.is_recurring,
        recurrence_pattern=expense_data.recurrence_pattern,
    )
    db.add(expense)
    await db.flush()
    await db.refresh(expense)
    return expense


@router.get("/", response_model=list[ExpenseResponse])
async def list_expenses(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    category_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_recurring: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[Expense]:
    query = select(Expense).where(Expense.deleted == False)

    if not include_recurring:
        query = query.where(Expense.is_recurring == False)
    if category_id:
        query = query.where(Expense.category_id == category_id)

    query = query.offset(skip).limit(limit).order_by(Expense.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/summary", response_model=dict)
async def get_expense_summary(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    query = select(
        Expense.category_id,
        func.sum(Expense.amount).label("total"),
        func.count(Expense.id).label("count"),
    ).where(Expense.deleted == False)

    if start_date:
        query = query.where(Expense.created_at >= start_date)
    if end_date:
        query = query.where(Expense.created_at <= end_date)

    query = query.group_by(Expense.category_id)
    result = await db.execute(query)

    total_result = await db.execute(
        select(func.sum(Expense.amount)).where(Expense.deleted == False)
    )
    total = total_result.scalar() or 0

    return {
        "total": total,
        "by_category": [{"category_id": r[0], "total": r[1], "count": r[2]} for r in result.all()],
    }


@router.post("/cash-ups", response_model=CashUpResponse, status_code=status.HTTP_201_CREATED)
async def create_cash_up(
    cash_up_data: CashUpCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> CashUp:
    variance = cash_up_data.actual_cash - cash_up_data.expected_cash

    cash_up = CashUp(
        employee_id=current_user.id,
        expected_cash=cash_up_data.expected_cash,
        actual_cash=cash_up_data.actual_cash,
        variance=variance,
        note=cash_up_data.note,
    )
    db.add(cash_up)
    await db.flush()
    await db.refresh(cash_up)
    return cash_up


@router.get("/cash-ups", response_model=list[CashUpResponse])
async def list_cash_ups(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[CashUp]:
    query = select(CashUp).offset(skip).limit(limit).order_by(CashUp.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Expense:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = result.scalar_one_or_none()
    if expense is None or expense.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    expense_data: ExpenseUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Expense:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = result.scalar_one_or_none()
    if expense is None or expense.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    update_data = expense_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)

    await db.flush()
    await db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> None:
    result = await db.execute(select(Expense).where(Expense.id == expense_id))
    expense = result.scalar_one_or_none()
    if expense is None or expense.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    expense.deleted = True
    await db.flush()