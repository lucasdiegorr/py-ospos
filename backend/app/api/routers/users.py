"""User account management endpoints (users capability).

Role gating (enforced by ``require_role`` once auth wires JWT decoding):

- Create, edit, deactivate/reactivate, and admin password reset: admin only.
- List/search: manager or admin.
- Self password change: any authenticated user.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.models.user import User
from app.services.users import (
    UserError,
    change_own_password,
    create_user,
    deactivate_user,
    list_users,
    reactivate_user,
    reset_password,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]


def _role_dependency(*roles: Role) -> Callable[..., CurrentUser]:
    """Return the ``require_role`` dependency callable for the given roles.

    ``require_role`` is annotated as ``Annotated[CurrentUser, Depends]`` but
    returns a callable at runtime; this helper narrows the type so the callable
    can be reused both as a ``Depends`` argument and as an override key in
    tests, until the auth capability wires real JWT decoding.
    """
    return cast(Callable[..., CurrentUser], require_role(*roles))


# Module-level dependencies, bound here so tests can override them through
# ``app.dependency_overrides``.
admin_required = _role_dependency(Role.ADMIN)
manager_admin_required = _role_dependency(Role.MANAGER, Role.ADMIN)
authenticated_required = _role_dependency(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)

AdminUser = Annotated[CurrentUser, Depends(admin_required)]
ManagerAdminUser = Annotated[CurrentUser, Depends(manager_admin_required)]
AuthenticatedUser = Annotated[CurrentUser, Depends(authenticated_required)]


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=128)
    role: Role


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    username: str | None = Field(default=None, min_length=1, max_length=120)
    role: Role | None = None
    password: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "UserUpdate":
        if all(value is None for value in (self.name, self.username, self.role, self.password)):
            raise ValueError("At least one field must be provided")
        return self


class ChangeOwnPassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class ResetPassword(BaseModel):
    new_password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: Role
    is_active: bool
    created_at: datetime


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    db: DbSession,
    current: AdminUser,
) -> User:
    """Create a user account (admin only)."""
    try:
        return create_user(
            db,
            name=payload.name,
            username=payload.username,
            password=payload.password,
            role=payload.role,
        )
    except UserError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("", response_model=list[UserOut])
def list_users_endpoint(
    db: DbSession,
    current: ManagerAdminUser,
    q: str | None = None,
) -> list[User]:
    """List and search users by name or username (manager or admin)."""
    return list_users(db, search=q)


@router.post("/me/password", response_model=UserOut)
def change_own_password_endpoint(
    payload: ChangeOwnPassword,
    db: DbSession,
    current: AuthenticatedUser,
) -> User:
    """Change the current user's password (requires the current password)."""
    try:
        return change_own_password(
            db,
            user_id=current.user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except UserError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/{user_id}", response_model=UserOut)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdate,
    db: DbSession,
    current: AdminUser,
) -> User:
    """Edit a user's name, username, role, or password (admin only)."""
    try:
        return update_user(
            db,
            user_id=user_id,
            name=payload.name,
            username=payload.username,
            role=payload.role,
            password=payload.password,
        )
    except UserError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user_endpoint(
    user_id: int,
    db: DbSession,
    current: AdminUser,
) -> User:
    """Deactivate a user account; refuses to deactivate the last active admin."""
    try:
        return deactivate_user(db, user_id=user_id)
    except UserError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{user_id}/reactivate", response_model=UserOut)
def reactivate_user_endpoint(
    user_id: int,
    db: DbSession,
    current: AdminUser,
) -> User:
    """Re-enable a deactivated user account (admin only)."""
    try:
        return reactivate_user(db, user_id=user_id)
    except UserError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/{user_id}/password", response_model=UserOut)
def reset_password_endpoint(
    user_id: int,
    payload: ResetPassword,
    db: DbSession,
    current: AdminUser,
) -> User:
    """Admin reset of another user's password."""
    try:
        return reset_password(db, user_id=user_id, new_password=payload.new_password)
    except UserError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
