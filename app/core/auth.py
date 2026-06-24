from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import decode_token, verify_password
from app.models.employee import Employee

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


CurrentUserDep = Annotated[Employee, Depends(get_current_user)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]