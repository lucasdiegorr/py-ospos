"""User account management (users capability).

Business rules enforced here:

- Every account has exactly one of three roles: attendant, manager, admin.
- The last active admin is protected: removing the only active admin (via
  deactivation or a role change away from admin) is refused.
- Passwords are stored as bcrypt hashes; plaintext is never persisted.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import Role
from app.models.user import User
from app.services.passwords import hash_password, verify_password


class UserError(Exception):
    """Base class for user service errors."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UserNotFoundError(UserError):
    status_code = 404


class UsernameTakenError(UserError):
    status_code = 409


class LastActiveAdminError(UserError):
    status_code = 400


class InvalidCurrentPasswordError(UserError):
    status_code = 400


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")
    return user


def _username_exists(db: Session, username: str, *, exclude_id: int | None = None) -> bool:
    stmt = select(User.id).where(User.username == username)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return db.execute(stmt).first() is not None


def _ensure_active_admin_remains(
    db: Session,
    user: User,
    *,
    new_role: Role | None = None,
    deactivating: bool = False,
) -> None:
    """Refuse changes that would remove the last active admin account.

    The invariant protects the only active admin from being deactivated or
    demoted to a non-admin role.
    """
    if Role(user.role) != Role.ADMIN:
        return
    removes_admin = deactivating or (new_role is not None and new_role != Role.ADMIN)
    if not removes_admin:
        return
    other_active_admins = db.execute(
        select(func.count())
        .select_from(User)
        .where(User.role == Role.ADMIN.value, User.is_active.is_(True), User.id != user.id)
    ).scalar_one()
    if other_active_admins == 0:
        raise LastActiveAdminError("Cannot deactivate or demote the last active admin")


def create_user(db: Session, *, name: str, username: str, password: str, role: Role) -> User:
    """Create an active user account with the given role."""
    if _username_exists(db, username):
        raise UsernameTakenError(f"Username {username!r} is already taken")
    user = User(
        name=name,
        username=username,
        password_hash=hash_password(password),
        role=role.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    *,
    user_id: int,
    name: str | None = None,
    username: str | None = None,
    role: Role | None = None,
    password: str | None = None,
) -> User:
    """Update a user's name, username, role, or password."""
    user = _get_user_or_404(db, user_id)
    if username is not None and username != user.username:
        if _username_exists(db, username, exclude_id=user.id):
            raise UsernameTakenError(f"Username {username!r} is already taken")
        user.username = username
    if name is not None:
        user.name = name
    if role is not None:
        _ensure_active_admin_remains(db, user, new_role=role)
        user.role = role.value
    if password is not None:
        user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, *, user_id: int) -> User:
    """Deactivate a user account; the last active admin is protected."""
    user = _get_user_or_404(db, user_id)
    _ensure_active_admin_remains(db, user, deactivating=True)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


def reactivate_user(db: Session, *, user_id: int) -> User:
    """Re-enable a deactivated user account."""
    user = _get_user_or_404(db, user_id)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, *, user_id: int, new_password: str) -> User:
    """Admin reset of another user's password; clears lockout state."""
    user = _get_user_or_404(db, user_id)
    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    db.refresh(user)
    return user


def change_own_password(
    db: Session, *, user_id: int, current_password: str, new_password: str
) -> User:
    """Change a user's own password after verifying the current one."""
    user = _get_user_or_404(db, user_id)
    if not verify_password(current_password, user.password_hash):
        raise InvalidCurrentPasswordError("Current password is incorrect")
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, *, search: str | None = None) -> list[User]:
    """List users, optionally filtering by a name or username fragment.

    Both active and inactive accounts are returned, ordered by name.
    """
    stmt = select(User).order_by(User.name)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(User.name.ilike(pattern), User.username.ilike(pattern)))
    return list(db.execute(stmt).scalars())
