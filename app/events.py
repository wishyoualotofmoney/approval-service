from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from .models import AuditLog, OutboxEvent

if TYPE_CHECKING:
    from .repository import ApprovalRepository

AGGREGATE_TYPE = "approval_request"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def record_audit(
    repo: "ApprovalRepository",
    *,
    workspace_id: str,
    request_id: str,
    action: str,
    actor_user_id: str,
    summary: dict,
) -> None:
    """Append an audit-trail entry. `summary` must contain only safe fields."""
    repo.add(
        AuditLog(
            id=_new_id("aud"),
            workspace_id=workspace_id,
            request_id=request_id,
            action=action,
            actor_user_id=actor_user_id,
            summary=summary,
        )
    )


def emit_event(
    repo: "ApprovalRepository",
    *,
    workspace_id: str,
    aggregate_id: str,
    event_type: str,
    payload: dict,
) -> None:
    """Write an event to the transactional outbox (safe payload only)."""
    repo.add(
        OutboxEvent(
            id=_new_id("evt"),
            workspace_id=workspace_id,
            aggregate_type=AGGREGATE_TYPE,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
        )
    )
