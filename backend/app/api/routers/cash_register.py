"""Cash-register capability router: the cash shift lifecycle.

Opening/closing shifts and supply/bleed movements are open to attendants,
managers, and admins (the acting user is recorded on the shift). Closing is
limited to the shift's owner unless the actor is a manager or admin.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.models.cash_register import Shift
from app.services import cash_register as service
from app.services.cash_register import (
    InvalidMovementError,
    ShiftAlreadyOpenError,
    ShiftClosedError,
    ShiftError,
    ShiftNotFound,
    ShiftPermissionError,
)

router = APIRouter(prefix="/shifts", tags=["cash-register"])

DbSession = Annotated[Session, Depends(get_db)]


def _role_dependency(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a role-checked current-user dependency (typed for ``Depends``)."""
    return cast(Callable[..., CurrentUser], require_role(*roles))


attendant_or_higher = _role_dependency(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)

AttendantDependency = Annotated[CurrentUser, Depends(attendant_or_higher)]


class ShiftOpen(BaseModel):
    float_cents: int = Field(ge=0)


class MovementIn(BaseModel):
    type: Literal["supply", "bleed"]
    amount_cents: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=300)


class ShiftClose(BaseModel):
    counted_cents: int = Field(ge=0)


class ShiftOut(BaseModel):
    id: int
    attendant_id: int
    float_cents: int
    status: str
    opened_at: datetime
    closed_at: datetime | None
    counted_cents: int | None


class MovementOut(BaseModel):
    id: int
    shift_id: int
    type: str
    amount_cents: int
    reason: str | None
    created_at: datetime


class ShiftSummaryOut(BaseModel):
    id: int
    status: str
    attendant_id: int
    float_cents: int
    opened_at: datetime
    closed_at: datetime | None
    payment_totals: dict[str, int]
    supplies_cents: int
    bleeds_cents: int
    expected_cents: int
    counted_cents: int | None
    difference_cents: int | None


def _shift_out(shift: Shift) -> ShiftOut:
    return ShiftOut(
        id=shift.id,
        attendant_id=shift.attendant_id,
        float_cents=shift.float_cents,
        status=shift.status,
        opened_at=shift.opened_at,
        closed_at=shift.closed_at,
        counted_cents=shift.counted_cents,
    )


@router.post("", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def open_shift(body: ShiftOpen, db: DbSession, user: AttendantDependency) -> ShiftOut:
    """Open a cash shift with a starting float (attendant+)."""
    try:
        shift = service.open_shift(db, attendant_id=user.user_id, float_cents=body.float_cents)
    except ShiftAlreadyOpenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ShiftError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _shift_out(shift)


@router.get("/current", response_model=ShiftOut)
def current_shift(db: DbSession, user: AttendantDependency) -> ShiftOut:
    """Return the active shift, if any."""
    shift = service.active_shift(db)
    if shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active shift")
    return _shift_out(shift)


@router.get("", response_model=list[ShiftOut])
def list_shifts(
    db: DbSession,
    user: AttendantDependency,
    status_: str | None = Query(default=None, alias="status"),
) -> list[ShiftOut]:
    """List shifts, optionally filtered by status."""
    return [_shift_out(shift) for shift in service.list_shifts(db, status=status_)]


@router.get("/{shift_id}", response_model=ShiftSummaryOut)
def shift_summary(shift_id: int, db: DbSession, user: AttendantDependency) -> dict:
    """Closing summary: per-method totals, movements, expected/difference."""
    try:
        return service.shift_summary(db, shift_id)
    except ShiftNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{shift_id}/movements", response_model=MovementOut)
def record_movement(
    shift_id: int,
    body: MovementIn,
    db: DbSession,
    user: AttendantDependency,
) -> MovementOut:
    """Record a cash supply or bleed on an open shift (attendant+)."""
    try:
        movement = service.record_movement(
            db,
            shift_id=shift_id,
            type=body.type,
            amount_cents=body.amount_cents,
            reason=body.reason,
            actor_id=user.user_id,
        )
    except ShiftNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ShiftClosedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidMovementError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MovementOut(
        id=movement.id,
        shift_id=movement.shift_id,
        type=movement.type,
        amount_cents=movement.amount_cents,
        reason=movement.reason,
        created_at=movement.created_at,
    )


@router.post("/{shift_id}/close", response_model=ShiftSummaryOut)
def close_shift(
    shift_id: int,
    body: ShiftClose,
    db: DbSession,
    user: AttendantDependency,
) -> dict:
    """Close a shift with the counted cash, computing the difference."""
    try:
        service.close_shift(
            db,
            shift_id=shift_id,
            counted_cents=body.counted_cents,
            actor_id=user.user_id,
            actor_role=user.role,
        )
    except ShiftNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ShiftPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ShiftClosedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidMovementError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return service.shift_summary(db, shift_id)
