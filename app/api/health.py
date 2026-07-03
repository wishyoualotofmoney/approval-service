from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)):
    """Readiness: dependencies (the database) are reachable."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503, content={"status": "unavailable", "database": "down"}
        )
    return {"status": "ready", "database": "up"}
