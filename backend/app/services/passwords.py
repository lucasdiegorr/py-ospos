"""Shared password hashing utility.

Uses passlib's bcrypt CryptContext so that all capabilities hash and verify
passwords through the same code path and configuration.
"""

from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (via passlib)."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether the plaintext password matches the stored bcrypt hash."""
    return _pwd_context.verify(password, password_hash)
