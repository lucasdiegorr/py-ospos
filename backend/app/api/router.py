"""Router auto-discovery.

Scans ``app/api/routers`` for modules exposing a module-level ``router``
attribute and includes them in the application. A capability worktree only
needs to drop in a router module — no shared file edits required.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable

from fastapi import FastAPI

from app.api import routers


def include_capability_routers(app: FastAPI) -> None:
    """Include every router module found under ``app.api.routers``."""
    for module_info in pkgutil.iter_modules(routers.__path__):
        module = importlib.import_module(f"{routers.__name__}.{module_info.name}")
        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router)


def capability_router_ids() -> Iterable[str]:
    """Return the names of discovered capability router modules."""
    return (m.name for m in pkgutil.iter_modules(routers.__path__))
