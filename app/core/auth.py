from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import decode_token, verify_password
from app.models.employee import Employee
from app.models.role import EmployeePermission, EmployeeRole, Permission, RolePermission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def authenticate_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    username: str,
    password: str,
) -> Employee | None:
    result = await db.execute(select(Employee).where(Employee.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Employee:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_token(token)
    if token_data.sub is None:
        raise credentials_exception

    result = await db.execute(select(Employee).where(Employee.id == token_data.sub))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    return user


async def get_effective_permissions(
    db: AsyncSession,
    employee_id: str,
) -> set[str]:
    result = await db.execute(
        select(Permission.code)
        .select_from(Employee)
        .join(EmployeeRole, EmployeeRole.employee_id == Employee.id)
        .join(RolePermission, RolePermission.role_id == EmployeeRole.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(Employee.id == employee_id)
    )
    codes = set(result.scalars().all())

    direct_result = await db.execute(
        select(Permission.code)
        .select_from(Employee)
        .join(EmployeePermission, EmployeePermission.employee_id == Employee.id)
        .join(Permission, Permission.id == EmployeePermission.permission_id)
        .where(Employee.id == employee_id)
    )
    codes.update(direct_result.scalars().all())

    return codes


def require_permission(code: str):
    async def dependency(
        current_user: Employee = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )
        perms = await get_effective_permissions(db, current_user.id)
        if code not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    return dependency


CurrentUserDep = Annotated[Employee, Depends(get_current_user)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]