from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep, DbSessionDep
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customer"])


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Customer:
    customer = Customer(**customer_data.model_dump())
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.get("/", response_model=list[CustomerResponse])
async def list_customers(
    db: DbSessionDep,
    current_user: CurrentUserDep,
    search: str | None = Query(None, description="Search by name, email, or phone"),
    customer_type: str | None = Query(None, description="Filter by type (customer/supplier)"),
    include_inactive: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[Customer]:
    query = select(Customer).where(Customer.deleted == False)

    if not include_inactive:
        query = query.where(Customer.is_active == True)

    if customer_type:
        query = query.where(Customer.type == customer_type)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Customer.first_name.ilike(search_term),
                Customer.last_name.ilike(search_term),
                Customer.email.ilike(search_term),
                Customer.phone.ilike(search_term),
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Customer:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if customer is None or customer.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_data: CustomerUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Customer:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if customer is None or customer.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    await db.flush()
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> None:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete customers",
        )

    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()

    if customer is None or customer.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    customer.deleted = True
    await db.flush()