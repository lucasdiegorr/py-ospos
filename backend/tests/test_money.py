"""Tests for the money primitive (integer cents)."""

from decimal import Decimal

from app.domain.money import cents_total, from_cents, to_cents


def test_to_cents_from_decimal() -> None:
    assert to_cents(Decimal("12.50")) == 1250


def test_to_cents_from_string() -> None:
    assert to_cents("12.50") == 1250


def test_to_cents_rounds_to_cents() -> None:
    assert to_cents(Decimal("12.509")) == 1251


def test_from_cents() -> None:
    assert from_cents(1250) == Decimal("12.50")


def test_cents_total() -> None:
    assert cents_total([100, 250, 50]) == 400


def test_zero() -> None:
    assert to_cents(Decimal("0")) == 0
    assert from_cents(0) == Decimal("0")
