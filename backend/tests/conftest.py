"""Shared test fixtures.

DB-backed tests run against Postgres (default: the local ``ospos`` database,
or ``OSPOS_DATABASE_URL`` when set) inside an outer transaction that is rolled
back after each test, so no data is ever persisted. The ``client`` fixture
overrides the app's database session and RBAC dependency so endpoints can be
exercised end to end without auth wiring.
"""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (register all models on Base.metadata)
from app.core.security import CurrentUser, Role
from app.db import Base, get_db
from app.main import app

DEFAULT_DATABASE_URL = "postgresql+psycopg://ospos:ospos@localhost:5432/ospos"


def _database_url() -> str:
    return os.environ.get("OSPOS_DATABASE_URL", DEFAULT_DATABASE_URL)


@pytest.fixture()
def db_engine() -> Generator[Engine, None, None]:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """A session whose writes are rolled back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with database session and RBAC dependencies overridden."""
    from app.api.routers import customers as customers_router

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def fake_user() -> CurrentUser:
        return CurrentUser(user_id=1, username="test-manager", role=Role.MANAGER)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[customers_router.attendant_or_higher] = fake_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
