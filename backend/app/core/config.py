"""Application configuration loaded from environment variables.

Secrets (DB password, JWT secret) are never committed; they come from the
environment or a local, untracked `.env` file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OSPOS_", extra="ignore")

    app_name: str = "py-ospos"
    debug: bool = False

    database_url: str = "postgresql+psycopg://ospos:ospos@localhost:5432/ospos"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    login_max_attempts: int = 5
    login_lockout_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
