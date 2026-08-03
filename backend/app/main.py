"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api.router import include_capability_routers
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

# Auto-discover capability routers so parallel worktrees add endpoints without
# editing this file.
include_capability_routers(app)
