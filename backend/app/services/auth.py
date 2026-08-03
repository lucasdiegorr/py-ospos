"""Authentication services: password hashing and token issuance.

Access tokens are short-lived, stateless JWTs that encode the user id,
username and role so authorization decisions need no database round-trip.
Refresh tokens are opaque random values; only their SHA-256 digest is ever
stored, never the raw token.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

import bcrypt
from jose import jwt

from app.core.config import get_settings
from app.domain.idempotency import utcnow
from app.models.user import RefreshToken, User


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether the plaintext password matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash or invalid input: never raise, just fail verification.
        return False


def _password_bytes(password: str) -> bytes:
    # bcrypt only considers the first 72 bytes; truncate identically on hash
    # and verify so longer passwords keep working.
    return password.encode("utf-8")[:72]


def create_access_token(user: User, *, expires_delta: timedelta | None = None) -> str:
    """Issue a signed JWT access token for the user.

    ``sub`` carries the user id and the ``role`` claim allows authorization
    without a server round-trip. ``expires_delta`` overrides the configured
    lifetime (used by tests and short-lived credentials).
    """
    settings = get_settings()
    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def generate_refresh_token() -> str:
    """Return a new cryptographically random refresh token value."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 digest stored for a refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_refresh_token(user_id: int, *, raw: str | None = None) -> tuple[RefreshToken, str]:
    """Create an unsaved ``RefreshToken`` row plus its raw client value.

    Only the digest is stored on the row; the caller returns the raw value to
    the client exactly once.
    """
    settings = get_settings()
    raw_token = raw or generate_refresh_token()
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    return row, raw_token
