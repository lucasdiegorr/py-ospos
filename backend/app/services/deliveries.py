"""Delivery services: status tracking and delivery listing.

Deliveries are attached to a sale at completion (sales capability) with a
pending status; the address is fully optional. This module owns the status
lifecycle (pending → in_transit → delivered, strictly forward, with every
change recorded) and lists deliveries with their customer, destination
summary, and sale reference.
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.delivery import Delivery, DeliveryStatusEvent
from app.models.sales import Sale

STATUS_ORDER = {"pending": 0, "in_transit": 1, "delivered": 2}
VALID_STATUSES = tuple(STATUS_ORDER)


class DeliveryError(Exception):
    """Base class for delivery domain violations."""


class DeliveryNotFound(LookupError):
    """Raised when a delivery does not exist."""


class DeliveryStatusError(DeliveryError):
    """Raised when a delivery status transition is invalid."""


class DeliveryRow(NamedTuple):
    """A delivery as shown in listings, with customer and destination."""

    id: int
    sale_id: int
    status: str
    customer_name: str | None
    destination: str
    created_at: datetime


def update_delivery_status(
    db: Session,
    delivery_id: int,
    *,
    status: str,
    actor_id: int | None = None,
) -> Delivery:
    """Move a delivery forward along the status lifecycle, recording the change."""
    delivery = _delivery_or_404(db, delivery_id)
    if status not in STATUS_ORDER:
        raise DeliveryStatusError(f"Invalid delivery status: {status}")
    if STATUS_ORDER[status] <= STATUS_ORDER[delivery.status]:
        raise DeliveryStatusError(
            f"Can't move delivery {delivery_id} from {delivery.status} to {status}"
        )
    delivery.status = status
    db.add(
        DeliveryStatusEvent(
            delivery_id=delivery_id,
            status=status,
            actor_id=actor_id,
        )
    )
    db.commit()
    db.refresh(delivery)
    return delivery


def get_delivery(db: Session, delivery_id: int) -> Delivery:
    return _delivery_or_404(db, delivery_id)


def list_deliveries(
    db: Session,
    *,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
) -> list[DeliveryRow]:
    """List deliveries filtered by status and/or creation date, newest first."""
    stmt = (
        select(Delivery, Customer.name)
        .join(Sale, Delivery.sale_id == Sale.id)
        .outerjoin(Customer, Sale.customer_id == Customer.id)
    )
    if status is not None:
        stmt = stmt.where(Delivery.status == status)
    if date_from is not None:
        stmt = stmt.where(Delivery.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Delivery.created_at <= date_to)
    stmt = stmt.order_by(Delivery.created_at.desc()).limit(limit)
    return [
        DeliveryRow(
            id=delivery.id,
            sale_id=delivery.sale_id,
            status=delivery.status,
            customer_name=name,
            destination=_destination(delivery),
            created_at=delivery.created_at,
        )
        for delivery, name in db.execute(stmt)
    ]


def _delivery_or_404(db: Session, delivery_id: int) -> Delivery:
    delivery = db.scalar(
        select(Delivery).options(selectinload(Delivery.events)).where(Delivery.id == delivery_id)
    )
    if delivery is None:
        raise DeliveryNotFound(f"Unknown delivery: {delivery_id}")
    return delivery


def _destination(delivery: Delivery) -> str:
    """Summarize a delivery destination from whatever address parts exist."""
    parts = [
        delivery.street,
        delivery.number,
        delivery.district,
        delivery.complement,
        delivery.reference,
    ]
    return " ".join(part for part in parts if part).strip() or "—"
