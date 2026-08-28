"""Reporting capability router: management reports.

Every endpoint is restricted to managers and admins (attendants never open
reports, per the reporting spec). The UI overlays the pending-sync count from
``/reports/pending-sync`` (which reads the sync capability's outbox count) to
warn that the data may be incomplete.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.services import reporting as service

router = APIRouter(prefix="/reports", tags=["reporting"])

DbSession = Annotated[Session, Depends(get_db)]


def _role_dependency(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a role-checked current-user dependency (typed for ``Depends``)."""
    return cast(Callable[..., CurrentUser], require_role(*roles))


manager_or_higher = _role_dependency(Role.MANAGER, Role.ADMIN)

ManagerDependency = Annotated[CurrentUser, Depends(manager_or_higher)]


@router.get("/sales-by-period")
def sales_by_period(
    db: DbSession,
    user: ManagerDependency,
    period: Literal["day", "week", "month"] = "day",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Sales totals, counts, and average ticket grouped by day/week/month."""
    try:
        return service.sales_by_period(db, period=period, date_from=date_from, date_to=date_to)
    except service.ReportingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/best-sellers")
def best_sellers(
    db: DbSession,
    user: ManagerDependency,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict]:
    """Top-selling products by quantity and revenue over a period."""
    try:
        return service.best_sellers(db, date_from=date_from, date_to=date_to, limit=limit)
    except service.ReportingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/critical-stock")
def critical_stock(
    db: DbSession,
    user: ManagerDependency,
    window_days: int = Query(default=30, ge=1, le=365),
) -> dict:
    """Low-stock products and dated stock expiring within the window."""
    return service.critical_stock(db, window_days=window_days)


@router.get("/open-fiados")
def open_fiados(db: DbSession, user: ManagerDependency) -> list[dict]:
    """Customers with outstanding balances and their oldest debt."""
    return service.open_fiados(db)


@router.get("/cash-flow")
def cash_flow(
    db: DbSession,
    user: ManagerDependency,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Daily money in (sales + supplies) and out (bleeds) with a net balance."""
    try:
        return service.cash_flow(db, date_from=date_from, date_to=date_to)
    except service.ReportingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/margin")
def margin(
    db: DbSession,
    user: ManagerDependency,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """Per-product revenue and margin when a cost price is recorded."""
    try:
        return service.margin_by_product(db, date_from=date_from, date_to=date_to)
    except service.ReportingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/pending-sync")
def pending_sync(db: DbSession, user: ManagerDependency) -> dict[str, int]:
    """Server-side count of unsettled writes, for the pending-sync notice."""
    return {"pending_sync_count": service.pending_sync_count(db)}
