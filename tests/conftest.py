from __future__ import annotations

import os

# Point settings at a throwaway SQLite DB before app modules import settings.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_approval.db")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth import (
    ACTION_CANCEL,
    ACTION_CREATE,
    ACTION_DECIDE,
    ACTION_READ,
)
from app.db import get_session
from app.main import create_app
from app.models import Base

ALL_ACTIONS = ",".join(
    [ACTION_READ, ACTION_CREATE, ACTION_DECIDE, ACTION_CANCEL]
)


def auth_headers(
    workspace_id: str = "ws_1",
    user_id: str = "usr_1",
    actions: str = ALL_ACTIONS,
) -> dict:
    return {
        "X-Workspace-Id": workspace_id,
        "X-User-Id": user_id,
        "X-Actions": actions,
    }


@pytest_asyncio.fixture
async def engine(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    eng = create_async_engine(db_url, connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
def sessionmaker(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def client(engine, sessionmaker):
    async def _override_session():
        async with sessionmaker() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
