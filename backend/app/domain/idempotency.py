"""Idempotency keys for offline-first synchronization.

Every write that can originate offline carries a client-generated
idempotency key. The server stores processed keys so re-delivery of the
same payload does not create duplicates.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def new_idempotency_key() -> str:
    """Generate a new client-side idempotency key."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Timezone-aware UTC now, used for all system timestamps."""
    return datetime.now(UTC)
