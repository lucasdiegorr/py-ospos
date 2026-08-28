"""Deliveries capability router: status tracking and delivery listing.

Deliveries are created at sale completion (sales capability). This module
moves a delivery forward along its status lifecycle and lists deliveries by
status/date with their destination and sale reference. Only ``attendant`` or
higher is required: attendants mark deliveries in-transit and delivered.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db import get_db
from app.services import deliveries as service

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

DbSession = Annotated[Session, Depends(get_db)]


def _role_dependency(*roles: Role) -> Callable[..., CurrentUser]:
    """Build a role-checked current-user dependency (typed for ``Depends``)."""
    return cast(Callable[..., CurrentUser], require_role(*roles))


attendant_or_higher = _role_dependency(Role.ATTENDANT, Role.MANAGER, Role.ADMIN)

AttendantDependency = Annotated[CurrentUser, Depends(attendant_or_higher)]


class DeliveryStatusUpdate(BaseModel):
    status: Literal["in_transit", "delivered"]


class DeliveryEventOut(BaseModel):
    status: str
    actor_id: int | None
    created_at: datetime


class DeliveryOut(BaseModel):
    id: int
    sale_id: int
    status: str
    street: str | None
    number: str | None
    district: str | None
    complement: str | None
    reference: str | None
    created_at: datetime
    events: list[DeliveryEventOut]


class DeliveryRowOut(BaseModel):
    """A delivery in listings, with customer and destination summary."""

    id: int
    sale_id: int
    status: str
    customer_name: str | None
    destination: str
    created_at: datetime


def _delivery_out(delivery) -> DeliveryOut:
    return DeliveryOut(
        id=delivery.id,
        sale_id=delivery.sale_id,
        status=delivery.status,
        street=delivery.street,
        number=delivery.number,
        district=delivery.district,
        complement=delivery.complement,
        reference=delivery.reference,
        created_at=delivery.created_at,
        events=[
            DeliveryEventOut(
                status=event.status,
                actor_id=event.actor_id,
                created_at=event.created_at,
            )
            for event in delivery.events
        ],
    )


@router.get("", response_model=list[DeliveryRowOut])
def list_deliveries(
    db: DbSession,
    user: AttendantDependency,
    status_: str | None = Query(default=None, alias="status"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[service.DeliveryRow]:
    """List deliveries filtered by status and/or creation date (attendant+)."""
    return service.list_deliveries(
        db,
        status=status_,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/{delivery_id}", response_model=DeliveryOut)
def detail(delivery_id: int, db: DbSession, user: AttendantDependency) -> DeliveryOut:
    """Delivery detail with its status-change history."""
    try:
        return _delivery_out(service.get_delivery(db, delivery_id))
    except service.DeliveryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{delivery_id}/status", response_model=DeliveryOut)
def update_status(
    delivery_id: int,
    body: DeliveryStatusUpdate,
    db: DbSession,
    user: AttendantDependency,
) -> DeliveryOut:
    """Move a delivery forward on its status lifecycle (any authenticated user)."""
    try:
        delivery = service.update_delivery_status(
            db, delivery_id, status=body.status, actor_id=user.user_id
        )
    except service.DeliveryNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except service.DeliveryStatusError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _delivery_out(delivery)
