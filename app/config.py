from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "approval-service"
    environment: str = "local"
    log_level: str = "INFO"

    # Async driver URL used by the app at runtime.
    database_url: str = "sqlite+aiosqlite:///./approval.db"

    @property
    def database_url_sync(self) -> str:
        """Sync-driver variant of the URL, used by Alembic migrations."""
        return (
            self.database_url
            .replace("+asyncpg", "+psycopg2")
            .replace("+aiosqlite", "")
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
