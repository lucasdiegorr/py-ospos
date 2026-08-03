"""Authentication endpoints: login, token refresh, logout, current user."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import CurrentUser, require_role
from app.db import get_db
from app.domain.idempotency import utcnow
from app.models.user import RefreshToken, User
from app.services.auth import (
    build_refresh_token,
    create_access_token,
    hash_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class UserProfile(BaseModel):
    """Public profile returned alongside issued tokens."""

    id: int
    username: str
    name: str
    role: str


class CurrentUserProfile(BaseModel):
    """Identity decoded from a valid access token."""

    id: int
    username: str
    role: str


class TokenResponse(BaseModel):
    """A freshly issued token pair plus the user profile."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfile


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    """Persist a new refresh token and build the token-pair response."""
    access_token = create_access_token(user)
    refresh_row, refresh_raw = build_refresh_token(user.id)
    db.add(refresh_row)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_raw,
        user=UserProfile(
            id=user.id,
            username=user.username,
            name=user.name,
            role=user.role,
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate credentials and issue an access/refresh token pair."""
    settings = get_settings()
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    now = utcnow()
    if user.locked_until is not None and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked, try again later",
        )
    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.login_max_attempts:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_attempts = 0
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    user.failed_login_attempts = 0
    user.locked_until = None
    response = _issue_tokens(db, user)
    db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Rotate a valid refresh token into a fresh access/refresh pair."""
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(payload.refresh_token)
        )
    )
    now = utcnow()
    if record is None or record.revoked_at is not None or record.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token",
        )
    user = record.user
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token",
        )
    record.revoked_at = now  # rotation: the presented token is now spent
    response = _issue_tokens(db, user)
    db.commit()
    return response


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    """Revoke the presented refresh token, ending its session."""
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(payload.refresh_token)
        )
    )
    if record is not None and record.revoked_at is None:
        record.revoked_at = utcnow()
        db.commit()
    return {"detail": "Logged out"}


@router.get("/me", response_model=CurrentUserProfile)
def me(user: Annotated[CurrentUser, Depends(require_role())]) -> CurrentUserProfile:
    """Return the identity carried by the caller's access token."""
    return CurrentUserProfile(id=user.user_id, username=user.username, role=user.role)
