from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ApprovalRequest, IdempotencyKey, OutboxEvent


class ApprovalRepository:
    """Thin data-access layer. Every query is scoped by workspace_id."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, obj) -> None:
        self.session.add(obj)

    async def get(
        self, workspace_id: str, request_id: str, for_update: bool = False
    ) -> Optional[ApprovalRequest]:
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.workspace_id == workspace_id,
            ApprovalRequest.id == request_id,
        )
        if for_update:
            # No-op on SQLite; provides row locking on Postgres.
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        workspace_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[ApprovalRequest]:
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.workspace_id == workspace_id
        )
        if status:
            stmt = stmt.where(ApprovalRequest.status == status)
        stmt = (
            stmt.order_by(ApprovalRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_idempotency(
        self, workspace_id: str, key: str
    ) -> Optional[IdempotencyKey]:
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.workspace_id == workspace_id,
            IdempotencyKey.key == key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def outbox_for(self, workspace_id: str, aggregate_id: str) -> List[OutboxEvent]:
        stmt = select(OutboxEvent).where(
            OutboxEvent.workspace_id == workspace_id,
            OutboxEvent.aggregate_id == aggregate_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
