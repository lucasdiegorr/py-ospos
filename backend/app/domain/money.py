"""Money as integer cents.

All monetary amounts in the system are stored and manipulated as integer
cents (int) to avoid floating-point rounding errors. API boundaries convert
to/from decimal currency strings.
"""

from __future__ import annotations

from decimal import Decimal

CENTS_PER_UNIT = 100


def to_cents(value: Decimal | str | int | float) -> int:
    """Convert a currency value to integer cents.

    Accepts a Decimal, a currency string such as "12.50", an integer number
    of units, or a float. Raises ValueError on malformed input.
    """
    if isinstance(value, int):
        # Already in cents when the caller passes an int amount.
        return value
    if isinstance(value, float):
        value = Decimal(str(value))
    elif isinstance(value, str):
        value = Decimal(value)
    return int((value * CENTS_PER_UNIT).quantize(Decimal("1")))  # type: ignore[arg-type]


def from_cents(cents: int) -> Decimal:
    """Convert integer cents back to a Decimal currency value."""
    return Decimal(cents) / CENTS_PER_UNIT


def cents_total(values: list[int]) -> int:
    """Return the sum of integer-cent amounts."""
    return sum(values)
