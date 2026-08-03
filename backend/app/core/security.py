"""Role-based access control and token primitives.

Three fixed roles: ``attendant``, ``manager``, ``admin``. Access control is
centralized here so every endpoint module enforces the same rules instead of
re-implementing role checks.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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


def require_role(*roles: Role) -> Annotated[CurrentUser, Depends]:
    """Return a dependency that resolves the current user and enforces roles.

    Usage::

        @router.get("/reports")
        def list_reports(user: require_role(Role.MANAGER, Role.ADMIN)):
            ...
    """

    def dependency(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    ) -> CurrentUser:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        # Placeholder token parse: capabilities wire JWT decoding here in auth.
        settings = get_settings()
        token = credentials.credentials
        if token == settings.jwt_secret:  # dev-only placeholder
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token decoding not yet wired",
            )
        # Real decoding is implemented by the auth capability.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return dependency  # type: ignore[return-value]
