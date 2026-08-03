"""Role-based access control and token primitives.

Three fixed roles: ``attendant``, ``manager``, ``admin``. Access control is
centralized here so every endpoint module enforces the same rules instead of
re-implementing role checks.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings


class Role(StrEnum):
    ATTENDANT = "attendant"
    MANAGER = "manager"
    ADMIN = "admin"


# Rank order used to decide which roles satisfy a required minimum role.
ROLE_RANK = {Role.ATTENDANT: 0, Role.MANAGER: 1, Role.ADMIN: 2}


class CurrentUser:
    """Identity of the authenticated user resolved from the access token."""

    def __init__(self, *, user_id: int, username: str, role: Role) -> None:
        self.user_id = user_id
        self.username = username
        self.role = role


bearer_scheme = HTTPBearer(auto_error=False)

# Credentials injected by FastAPI from the Authorization: Bearer header.
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def decode_access_token(token: str) -> CurrentUser:
    """Decode and validate a JWT access token into a ``CurrentUser``.

    Raises ``HTTPException(401)`` for expired, malformed or invalid tokens.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
    sub = payload.get("sub")
    username = payload.get("username")
    role = payload.get("role")
    if sub is None or username is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    try:
        user_id = int(sub)
        user_role = Role(role)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    return CurrentUser(user_id=user_id, username=str(username), role=user_role)


def require_role(*roles: Role) -> Callable[[Credentials], CurrentUser]:
    """Return a dependency that resolves the current user and enforces roles.

    The caller's role must be at least the lowest of the given roles; calling
    with no arguments only requires a valid access token. Usage::

        from typing import Annotated
        from fastapi import Depends
        from app.core.security import CurrentUser, Role, require_role

        @router.get("/reports")
        def list_reports(
            user: Annotated[CurrentUser, Depends(require_role(Role.MANAGER, Role.ADMIN))],
        ):
            ...
    """

    def dependency(credentials: Credentials) -> CurrentUser:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        user = decode_access_token(credentials.credentials)
        if roles:
            required_rank = min(ROLE_RANK[role] for role in roles)
            if ROLE_RANK[user.role] < required_rank:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
        return user

    return dependency
