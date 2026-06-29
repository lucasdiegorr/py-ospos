from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep, DbSessionDep, get_effective_permissions, require_permission
from app.core.security import get_password_hash
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate

router = APIRouter(prefix="/employees", tags=["employee"])


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    db: DbSessionDep,
    _: None = Depends(require_permission("employees.create")),
) -> Employee:
    employee = Employee(
        username=employee_data.username,
        password_hash=get_password_hash(employee_data.password),
        first_name=employee_data.first_name,
        last_name=employee_data.last_name,
        email=employee_data.email,
        phone=employee_data.phone,
    )
    db.add(employee)
    await db.flush()
    await db.refresh(employee)
    return employee


@router.get("/me", response_model=EmployeeResponse)
async def get_current_employee(
    current_user: CurrentUserDep,
) -> Employee:
    return current_user


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Employee:
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    return employee


@router.patch("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: str,
    employee_data: EmployeeUpdate,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> Employee:
    is_self = current_user.id == employee_id
    if not is_self:
        perms = await get_effective_permissions(db, current_user.id)
        if "employees.update" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this employee",
            )

    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    update_data = employee_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    await db.flush()
    await db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: str,
    db: DbSessionDep,
    _: None = Depends(require_permission("employees.delete")),
) -> None:
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()

    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    employee.deleted = True
    await db.flush()