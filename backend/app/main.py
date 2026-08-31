"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from sqlalchemy import select

from alembic import command  # type: ignore[attr-defined]
from app.api.router import include_capability_routers
from app.core.config import get_settings
from app.core.security import Role
from app.db import SessionLocal
from app.models.user import User
from app.services.users import create_user

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(cfg, "head")


def _seed_admin_user() -> None:
    """Create the initial admin user from env vars if configured.

    No-op when admin_username/admin_password are not set. Idempotent: if a user
    with the given username already exists, it is left unchanged.
    """
    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        return
    db = SessionLocal()
    try:
        existing = db.execute(
            select(User).where(User.username == settings.admin_username)
        ).scalar_one_or_none()
        if existing is None:
            create_user(
                db,
                name=settings.admin_name or settings.admin_username,
                username=settings.admin_username,
                password=settings.admin_password,
                role=Role.ADMIN,
            )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    _run_migrations()
    _seed_admin_user()
    yield


settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# Auto-discover capability routers so parallel worktrees add endpoints without
# editing this file.
include_capability_routers(app)
