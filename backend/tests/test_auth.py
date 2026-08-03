"""Integration tests for the auth capability (against the local Postgres)."""

from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import Role, require_role
from app.db import SessionLocal
from app.domain.idempotency import utcnow
from app.main import app
from app.models.user import User
from app.services.auth import create_access_token, hash_password

client = TestClient(app)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def make_user(db: Session) -> Generator[Callable[..., User], None, None]:
    created: list[User] = []

    def _make(**overrides: Any) -> User:
        defaults: dict[str, Any] = {
            "username": f"user-{uuid4().hex[:12]}",
            "name": "Test User",
            "password_hash": hash_password("correct-password"),
            "role": "attendant",
            "is_active": True,
        }
        defaults.update(overrides)
        user = User(**defaults)
        db.add(user)
        db.commit()
        db.refresh(user)
        created.append(user)
        return user

    yield _make

    for user in created:
        db.delete(user)
        db.commit()


def _login(username: str, password: str):
    return client.post("/auth/login", json={"username": username, "password": password})


def _refresh(token: str):
    return client.post("/auth/refresh", json={"refresh_token": token})


def _me(token: str):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})


# --- Login -------------------------------------------------------------------


def test_login_success(make_user: Callable[..., User]) -> None:
    user = make_user()
    response = _login(user.username, "correct-password")
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": "attendant",
    }


def test_login_invalid_password_records_failure(
    make_user: Callable[..., User], db: Session
) -> None:
    user = make_user()
    response = _login(user.username, "wrong-password")
    assert response.status_code == 401
    fresh = db.get(User, user.id)
    assert fresh is not None
    db.refresh(fresh)
    assert fresh.failed_login_attempts == 1


def test_login_unknown_username() -> None:
    response = _login(f"ghost-{uuid4().hex[:8]}", "whatever")
    assert response.status_code == 401


def test_login_disabled_account(make_user: Callable[..., User]) -> None:
    user = make_user(is_active=False)
    response = _login(user.username, "correct-password")
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


# --- Access token checks ------------------------------------------------------


def test_me_with_valid_token_identifies_user(make_user: Callable[..., User]) -> None:
    user = make_user()
    response = _me(create_access_token(user))
    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        "role": "attendant",
    }


def test_me_rejects_expired_token(make_user: Callable[..., User]) -> None:
    user = make_user()
    token = create_access_token(user, expires_delta=timedelta(seconds=-10))
    assert _me(token).status_code == 401


def test_me_rejects_malformed_token() -> None:
    assert _me("not.a.jwt").status_code == 401


def test_me_requires_authentication() -> None:
    assert client.get("/auth/me").status_code == 401


def test_require_role_enforces_roles(make_user: Callable[..., User]) -> None:
    attendant = make_user(role="attendant")
    admin = make_user(role="admin")
    dependency = require_role(Role.MANAGER)
    with pytest.raises(HTTPException) as exc_info:
        dependency(
            HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=create_access_token(attendant)
            )
        )
    assert exc_info.value.status_code == 403
    granted = dependency(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=create_access_token(admin))
    )
    assert granted.user_id == admin.id


# --- Refresh rotation ---------------------------------------------------------


def test_refresh_rotates_token(make_user: Callable[..., User]) -> None:
    user = make_user()
    old_refresh = _login(user.username, "correct-password").json()["refresh_token"]
    response = _refresh(old_refresh)
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"] != old_refresh
    # The rotated token is invalid for further refreshes.
    assert _refresh(old_refresh).status_code == 401


def test_refresh_unknown_token_rejected() -> None:
    assert _refresh("not-a-real-refresh-token").status_code == 401


def test_refresh_revoked_token_rejected(make_user: Callable[..., User]) -> None:
    user = make_user()
    token = _login(user.username, "correct-password").json()["refresh_token"]
    client.post("/auth/logout", json={"refresh_token": token})
    assert _refresh(token).status_code == 401


# --- Logout -------------------------------------------------------------------


def test_logout_revokes_session(make_user: Callable[..., User]) -> None:
    user = make_user()
    token = _login(user.username, "correct-password").json()["refresh_token"]
    response = client.post("/auth/logout", json={"refresh_token": token})
    assert response.status_code == 200
    assert _refresh(token).status_code == 401


def test_logout_is_idempotent() -> None:
    response = client.post("/auth/logout", json={"refresh_token": "unknown-token"})
    assert response.status_code == 200


# --- Lockout ------------------------------------------------------------------


def test_lockout_after_repeated_failures(make_user: Callable[..., User]) -> None:
    user = make_user()
    for _ in range(5):
        assert _login(user.username, "wrong-password").status_code == 401
    # Blocked even with the correct password until the cooldown elapses.
    assert _login(user.username, "correct-password").status_code == 423


def test_lockout_clears_after_cooldown(make_user: Callable[..., User], db: Session) -> None:
    user = make_user()
    for _ in range(5):
        _login(user.username, "wrong-password")
    # Simulate the cooldown elapsing, then a valid login must succeed.
    user.locked_until = utcnow() - timedelta(minutes=1)
    db.commit()
    assert _login(user.username, "correct-password").status_code == 200
