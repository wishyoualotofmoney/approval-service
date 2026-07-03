from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceType(str, enum.Enum):
    publication = "publication"
    scenario = "scenario"
    edit = "edit"
    external = "external"


class Status(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


# Terminal states an approval request cannot leave once reached.
FINAL_STATUSES = {Status.approved, Status.rejected, Status.cancelled}


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)

    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_user_ids: Mapped[list] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(
        String(16), default=Status.pending.value, index=True
    )

    decision_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    """Append-only trail of every successful change (who / what / when)."""

    __tablename__ = "approval_audit_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(32))
    actor_user_id: Mapped[str] = mapped_column(String(128))
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class OutboxEvent(Base):
    """Transactional outbox: events a future publisher can relay to a broker."""

    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class IdempotencyKey(Base):
    """Stores the response of a first request so retries can be replayed."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_idempotency_ws_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(String(128))
    key: Mapped[str] = mapped_column(String(255))
    endpoint: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
