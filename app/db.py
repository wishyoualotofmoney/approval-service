from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

_settings = get_settings()

# SQLite needs check_same_thread relaxed; harmless / ignored for Postgres.
_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)

engine = create_async_engine(
    _settings.database_url,
    future=True,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session."""
    async with SessionLocal() as session:
        yield session
