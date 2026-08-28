"""Cash-register services: the cash shift lifecycle.

A shift is opened by an attendant with a starting float and is the single
active shift for the drawer; sales completed while it is open are attributed
to it (enforced by the sales router through ``require_active_shift``). During
the shift an attendant records cash supplies (suprimento) and bleeds
(sangria); at close the attendant's counted cash is compared with the
expected cash (float + cash sales + supplies − bleeds).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import Role
from app.domain.idempotency import utcnow
from app.models.cash_register import CashMovement, Shift
from app.services.payments import payment_totals_by_method

VALID_MOVEMENT_TYPES = ("supply", "bleed")


class ShiftError(Exception):
    """Base class for cash-register domain violations."""


class ShiftNotFound(LookupError):
    """Raised when a shift does not exist."""


class ShiftAlreadyOpenError(ShiftError):
    """Raised when opening a shift while another is already active."""


class ShiftClosedError(ShiftError):
    """Raised when mutating a closed shift."""


class ShiftNotOpenError(ShiftError):
    """Raised when a sale requires an active shift but none is open."""


class ShiftPermissionError(ShiftError):
    """Raised when a user tries to close someone else's shift."""


class InvalidMovementError(ShiftError):
    """Raised when a supply/bleed movement is invalid."""


def open_shift(db: Session, *, attendant_id: int | None, float_cents: int) -> Shift:
    """Open a new shift with a starting float; one active shift at a time."""
    if attendant_id is None:
        raise ShiftError("a shift must be opened by a user")
    if float_cents < 0:
        raise InvalidMovementError("float_cents must be non-negative")
    if active_shift(db) is not None:
        raise ShiftAlreadyOpenError("A shift is already open; close it before opening another")
    shift = Shift(attendant_id=attendant_id, float_cents=float_cents, status="open")
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


def active_shift(db: Session) -> Shift | None:
    """Return the single open shift, if any."""
    return db.scalar(select(Shift).where(Shift.status == "open").order_by(Shift.id))


def get_shift(db: Session, shift_id: int) -> Shift:
    shift = db.get(Shift, shift_id)
    if shift is None:
        raise ShiftNotFound(f"Unknown shift: {shift_id}")
    return shift


def require_active_shift(db: Session, shift_id: int | None) -> Shift:
    """Resolve the shift that a sale must belong to.

    With a ``shift_id`` the shift must exist and be open; without one the
    current active shift is used. Raises ``ShiftNotOpenError`` when no shift
    can cover the sale.
    """
    if shift_id is not None:
        shift = get_shift(db, shift_id)
        if shift.status != "open":
            raise ShiftClosedError(f"Shift {shift_id} is closed")
        return shift
    fallback = active_shift(db)
    if fallback is None:
        raise ShiftNotOpenError("Open a cash shift before completing a sale")
    return fallback


def record_movement(
    db: Session,
    *,
    shift_id: int,
    type: str,
    amount_cents: int,
    reason: str,
    actor_id: int | None = None,
) -> CashMovement:
    """Record a cash supply (suprimento) or bleed (sangria) on an open shift."""
    shift = get_shift(db, shift_id)
    if shift.status != "open":
        raise ShiftClosedError(f"Shift {shift_id} is closed")
    if type not in VALID_MOVEMENT_TYPES:
        raise InvalidMovementError(f"Invalid movement type: {type}")
    if amount_cents <= 0:
        raise InvalidMovementError("amount_cents must be positive")
    if not reason.strip():
        raise InvalidMovementError("reason is required")
    movement = CashMovement(
        shift_id=shift_id,
        type=type,
        amount_cents=amount_cents,
        reason=reason.strip(),
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


def expected_cash(db: Session, shift_id: int) -> int:
    """Float + cash sales + supplies − bleeds."""
    shift = get_shift(db, shift_id)
    cash_sales = payment_totals_by_method(db, shift_id).get("cash", 0)
    supplies = _movement_total(db, shift_id, "supply")
    bleeds = _movement_total(db, shift_id, "bleed")
    return shift.float_cents + cash_sales + supplies - bleeds


def close_shift(
    db: Session,
    *,
    shift_id: int,
    counted_cents: int,
    actor_id: int | None,
    actor_role: Role,
) -> Shift:
    """Close a shift with the counted cash; compute the difference."""
    if counted_cents < 0:
        raise InvalidMovementError("counted_cents must be non-negative")
    shift = get_shift(db, shift_id)
    if shift.status != "open":
        raise ShiftClosedError(f"Shift {shift_id} is already closed")
    if actor_role not in (Role.MANAGER, Role.ADMIN) and shift.attendant_id != actor_id:
        raise ShiftPermissionError("Only the shift's attendant or a manager can close it")
    shift.status = "closed"
    shift.counted_cents = counted_cents
    shift.closed_at = utcnow()
    db.commit()
    db.refresh(shift)
    return shift


def shift_summary(db: Session, shift_id: int) -> dict:
    """Closing summary: per-method payments, movements, expected, difference."""
    shift = get_shift(db, shift_id)
    expected = expected_cash(db, shift_id)
    counted = shift.counted_cents
    return {
        "id": shift_id,
        "status": shift.status,
        "attendant_id": shift.attendant_id,
        "float_cents": shift.float_cents,
        "opened_at": shift.opened_at,
        "closed_at": shift.closed_at,
        "payment_totals": payment_totals_by_method(db, shift_id),
        "supplies_cents": _movement_total(db, shift_id, "supply"),
        "bleeds_cents": _movement_total(db, shift_id, "bleed"),
        "expected_cents": expected,
        "counted_cents": counted,
        "difference_cents": (counted - expected) if counted is not None else None,
    }


def list_shifts(db: Session, *, status: str | None = None) -> list[Shift]:
    stmt = select(Shift).order_by(Shift.id)
    if status is not None:
        stmt = stmt.where(Shift.status == status)
    return list(db.scalars(stmt))


def _movement_total(db: Session, shift_id: int, type: str) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(CashMovement.amount_cents), 0)).where(
            CashMovement.shift_id == shift_id, CashMovement.type == type
        )
    )
    return int(total or 0)
