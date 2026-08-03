"""Tests for the users capability: service layer and role-gated endpoints."""

from collections.abc import Callable, Generator

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (register all models on Base.metadata)
from app.api.routers.users import (
    admin_required,
    authenticated_required,
    manager_admin_required,
)
from app.core.security import CurrentUser, Role
from app.db import Base, get_db
from app.main import app
from app.models.user import User
from app.services.users import (
    InvalidCurrentPasswordError,
    LastActiveAdminError,
    UsernameTakenError,
    UserNotFoundError,
    change_own_password,
    create_user,
    deactivate_user,
    list_users,
    reactivate_user,
    reset_password,
    update_user,
    verify_password,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """In-memory SQLite session with just the users table."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _install_auth_overrides(current: CurrentUser) -> None:
    """Install role-gating dependency overrides for the given current user.

    Mirrors the enforcement ``require_role`` performs once the auth capability
    wires JWT decoding into the placeholder in ``app.core.security``.
    """

    def gate(*allowed: Role) -> Callable[[], CurrentUser]:
        def dependency() -> CurrentUser:
            if current.role not in allowed:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return current

        return dependency

    app.dependency_overrides[admin_required] = gate(Role.ADMIN)
    app.dependency_overrides[manager_admin_required] = gate(Role.MANAGER, Role.ADMIN)
    app.dependency_overrides[authenticated_required] = gate(
        Role.ATTENDANT, Role.MANAGER, Role.ADMIN
    )


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with the in-memory DB and clean dependency overrides."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _admin() -> CurrentUser:
    return CurrentUser(user_id=1, username="admin", role=Role.ADMIN)


def _manager() -> CurrentUser:
    return CurrentUser(user_id=2, username="manager", role=Role.MANAGER)


def _attendant() -> CurrentUser:
    return CurrentUser(user_id=3, username="attendant", role=Role.ATTENDANT)


# ---------------------------------------------------------------------------
# Service layer
# ---------------------------------------------------------------------------


def test_create_user_hashes_password_and_defaults_active(db_session: Session) -> None:
    user = create_user(
        db_session, name="Ana Souza", username="ana", password="secret123", role=Role.ATTENDANT
    )
    assert user.id is not None
    assert user.is_active is True
    assert user.role == "attendant"
    assert user.password_hash != "secret123"
    assert verify_password("secret123", user.password_hash)
    assert user.created_at is not None


def test_create_user_duplicate_username_rejected(db_session: Session) -> None:
    create_user(db_session, name="Ana", username="ana", password="x", role=Role.ATTENDANT)
    with pytest.raises(UsernameTakenError):
        create_user(db_session, name="Outra", username="ana", password="x", role=Role.MANAGER)


def test_update_user_fields_and_password(db_session: Session) -> None:
    user = create_user(
        db_session, name="Ana", username="ana", password="oldpass", role=Role.ATTENDANT
    )
    updated = update_user(
        db_session,
        user_id=user.id,
        name="Ana Souza",
        username="ana.s",
        role=Role.MANAGER,
        password="newpass",
    )
    assert updated.name == "Ana Souza"
    assert updated.username == "ana.s"
    assert updated.role == "manager"
    assert verify_password("newpass", updated.password_hash)
    assert not verify_password("oldpass", updated.password_hash)


def test_update_user_duplicate_username_rejected(db_session: Session) -> None:
    create_user(db_session, name="Ana", username="ana", password="x", role=Role.ATTENDANT)
    other = create_user(db_session, name="Bia", username="bia", password="x", role=Role.ATTENDANT)
    with pytest.raises(UsernameTakenError):
        update_user(db_session, user_id=other.id, username="ana")


def test_update_unknown_user_raises(db_session: Session) -> None:
    with pytest.raises(UserNotFoundError):
        update_user(db_session, user_id=999, name="X")


def test_deactivate_and_reactivate(db_session: Session) -> None:
    user = create_user(db_session, name="Ana", username="ana", password="x", role=Role.ATTENDANT)
    assert deactivate_user(db_session, user_id=user.id).is_active is False
    assert reactivate_user(db_session, user_id=user.id).is_active is True


def test_cannot_deactivate_last_active_admin(db_session: Session) -> None:
    admin = create_user(db_session, name="Root", username="root", password="x", role=Role.ADMIN)
    with pytest.raises(LastActiveAdminError):
        deactivate_user(db_session, user_id=admin.id)


def test_cannot_demote_last_active_admin(db_session: Session) -> None:
    admin = create_user(db_session, name="Root", username="root", password="x", role=Role.ADMIN)
    with pytest.raises(LastActiveAdminError):
        update_user(db_session, user_id=admin.id, role=Role.MANAGER)


def test_deactivate_admin_allowed_when_another_active_admin_exists(db_session: Session) -> None:
    first = create_user(db_session, name="A", username="a", password="x", role=Role.ADMIN)
    create_user(db_session, name="B", username="b", password="x", role=Role.ADMIN)
    assert deactivate_user(db_session, user_id=first.id).is_active is False


def test_admin_reset_password_invalidates_old(db_session: Session) -> None:
    user = create_user(
        db_session, name="Ana", username="ana", password="oldpass", role=Role.ATTENDANT
    )
    reset = reset_password(db_session, user_id=user.id, new_password="newpass")
    assert verify_password("newpass", reset.password_hash)
    assert not verify_password("oldpass", reset.password_hash)


def test_change_own_password_requires_current(db_session: Session) -> None:
    user = create_user(
        db_session, name="Ana", username="ana", password="oldpass", role=Role.ATTENDANT
    )
    with pytest.raises(InvalidCurrentPasswordError):
        change_own_password(
            db_session, user_id=user.id, current_password="wrong", new_password="newpass"
        )
    changed = change_own_password(
        db_session, user_id=user.id, current_password="oldpass", new_password="newpass"
    )
    assert verify_password("newpass", changed.password_hash)


def test_list_users_search_includes_inactive(db_session: Session) -> None:
    create_user(db_session, name="Ana Souza", username="ana", password="x", role=Role.ATTENDANT)
    bia = create_user(db_session, name="Bia Lima", username="bia", password="x", role=Role.MANAGER)
    deactivate_user(db_session, user_id=bia.id)
    create_user(db_session, name="Carlos", username="carlos", password="x", role=Role.ADMIN)

    by_name = list_users(db_session, search="Souza")
    assert [u.username for u in by_name] == ["ana"]

    by_username = list_users(db_session, search="bia")
    assert [u.username for u in by_username] == ["bia"]

    assert len(list_users(db_session)) == 3


# ---------------------------------------------------------------------------
# Router: role gating and endpoints
# ---------------------------------------------------------------------------


def test_create_user_as_admin_returns_201(client: TestClient, db_session: Session) -> None:
    _install_auth_overrides(_admin())
    response = client.post(
        "/users",
        json={"name": "Ana Souza", "username": "ana", "password": "secret123", "role": "attendant"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "ana"
    assert body["role"] == "attendant"
    assert body["is_active"] is True
    assert "password" not in body
    assert verify_password("secret123", db_session.get(User, body["id"]).password_hash)


def test_create_user_as_attendant_denied(client: TestClient) -> None:
    _install_auth_overrides(_attendant())
    response = client.post(
        "/users",
        json={"name": "X", "username": "x", "password": "secret123", "role": "attendant"},
    )
    assert response.status_code == 403


def test_create_user_duplicate_username_conflict(client: TestClient) -> None:
    _install_auth_overrides(_admin())
    first = client.post(
        "/users",
        json={"name": "Ana", "username": "ana", "password": "secret123", "role": "attendant"},
    )
    assert first.status_code == 201
    response = client.post(
        "/users",
        json={"name": "Bia", "username": "ana", "password": "secret123", "role": "manager"},
    )
    assert response.status_code == 409


def test_edit_user_as_admin_changes_role(client: TestClient, db_session: Session) -> None:
    _install_auth_overrides(_admin())
    created = client.post(
        "/users",
        json={"name": "Ana", "username": "ana", "password": "secret123", "role": "attendant"},
    )
    uid = created.json()["id"]
    response = client.patch(f"/users/{uid}", json={"role": "manager", "name": "Ana Souza"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "manager"
    assert body["name"] == "Ana Souza"
    # Role is persisted; new access tokens issued after this carry "manager".
    assert db_session.get(User, uid).role == "manager"


def test_edit_user_as_manager_denied(client: TestClient) -> None:
    _install_auth_overrides(_manager())
    response = client.patch("/users/1", json={"name": "X"})
    assert response.status_code == 403


def test_edit_unknown_user_404(client: TestClient) -> None:
    _install_auth_overrides(_admin())
    response = client.patch("/users/999", json={"name": "X"})
    assert response.status_code == 404


def test_deactivate_and_reactivate_endpoints(client: TestClient, db_session: Session) -> None:
    _install_auth_overrides(_admin())
    user = create_user(db_session, name="Ana", username="ana", password="x", role=Role.ATTENDANT)
    assert client.post(f"/users/{user.id}/deactivate").json()["is_active"] is False
    assert client.post(f"/users/{user.id}/reactivate").json()["is_active"] is True


def test_deactivate_last_active_admin_refused(client: TestClient, db_session: Session) -> None:
    _install_auth_overrides(_admin())
    admin = create_user(db_session, name="Root", username="root", password="x", role=Role.ADMIN)
    response = client.post(f"/users/{admin.id}/deactivate")
    assert response.status_code == 400
    assert "last active admin" in response.json()["detail"].lower()


def test_admin_reset_password_endpoint(client: TestClient, db_session: Session) -> None:
    _install_auth_overrides(_admin())
    user = create_user(
        db_session, name="Ana", username="ana", password="oldpass", role=Role.ATTENDANT
    )
    response = client.post(f"/users/{user.id}/password", json={"new_password": "newpass"})
    assert response.status_code == 200
    assert verify_password("newpass", db_session.get(User, user.id).password_hash)
    assert not verify_password("oldpass", db_session.get(User, user.id).password_hash)


def test_self_change_password_endpoint(client: TestClient, db_session: Session) -> None:
    user = create_user(
        db_session, name="Ana", username="ana", password="oldpass", role=Role.ATTENDANT
    )
    _install_auth_overrides(CurrentUser(user_id=user.id, username="ana", role=Role.ATTENDANT))
    response = client.post(
        "/users/me/password",
        json={"current_password": "oldpass", "new_password": "newpass"},
    )
    assert response.status_code == 200
    assert verify_password("newpass", db_session.get(User, user.id).password_hash)


def test_self_change_password_wrong_current_rejected(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(
        db_session, name="Ana", username="ana", password="oldpass", role=Role.ATTENDANT
    )
    _install_auth_overrides(CurrentUser(user_id=user.id, username="ana", role=Role.ATTENDANT))
    response = client.post(
        "/users/me/password",
        json={"current_password": "wrong", "new_password": "newpass"},
    )
    assert response.status_code == 400


def test_list_users_as_manager_includes_inactive(client: TestClient, db_session: Session) -> None:
    create_user(db_session, name="Ana Souza", username="ana", password="x", role=Role.ATTENDANT)
    bia = create_user(db_session, name="Bia Lima", username="bia", password="x", role=Role.MANAGER)
    deactivate_user(db_session, user_id=bia.id)
    _install_auth_overrides(_manager())
    response = client.get("/users", params={"q": "a"})
    assert response.status_code == 200
    body = response.json()
    assert {u["username"] for u in body} == {"ana", "bia"}
    assert {u["is_active"] for u in body} == {True, False}


def test_list_users_as_attendant_denied(client: TestClient) -> None:
    _install_auth_overrides(_attendant())
    assert client.get("/users").status_code == 403
