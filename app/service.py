from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from . import events
from .auth import Principal
from .errors import ConflictError, NotFoundError
from .models import (
    FINAL_STATUSES,
    ApprovalRequest,
    IdempotencyKey,
    Status,
)
from .repository import ApprovalRepository
from .schemas import (
    ApprovalRequestListOut,
    ApprovalRequestOut,
    ApproveIn,
    CancelIn,
    CreateApprovalRequestIn,
    DecisionOut,
    RejectIn,
)

# Endpoint -> terminal status produced by that decision.
_DECISION_TARGET = {
    "approve": Status.approved,
    "reject": Status.rejected,
    "cancel": Status.cancelled,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_request_id() -> str:
    return f"areq_{uuid.uuid4().hex}"


def _fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def to_out(model: ApprovalRequest) -> ApprovalRequestOut:
    decision: Optional[DecisionOut] = None
    if model.status != Status.pending.value:
        decision = DecisionOut(
            comment=model.decision_comment,
            reason=model.decision_reason,
            decided_by=model.decided_by,
            decided_at=model.decided_at,
        )
    return ApprovalRequestOut(
        id=model.id,
        workspace_id=model.workspace_id,
        source_type=model.source_type,
        source_id=model.source_id,
        title=model.title,
        description=model.description,
        reviewer_user_ids=model.reviewer_user_ids or [],
        status=model.status,
        decision=decision,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _body(model: ApprovalRequest) -> dict:
    return to_out(model).model_dump(by_alias=True, mode="json")


def _safe_event_payload(model: ApprovalRequest) -> dict:
    """Event payload with identifiers only - no free-text / secret-bearing fields."""
    return {
        "id": model.id,
        "workspaceId": model.workspace_id,
        "sourceType": model.source_type,
        "sourceId": model.source_id,
        "status": model.status,
        "reviewerUserIds": model.reviewer_user_ids or [],
        "decidedBy": model.decided_by,
        "occurredAt": _now().isoformat(),
    }


class ApprovalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ApprovalRepository(session)

    # ------------------------------------------------------------------ #
    # Idempotency helpers
    # ------------------------------------------------------------------ #
    async def _replay(
        self, workspace_id: str, key: Optional[str], fingerprint: str
    ) -> Optional[Tuple[int, dict]]:
        if not key:
            return None
        existing = await self.repo.get_idempotency(workspace_id, key)
        if existing is None:
            return None
        if existing.request_hash != fingerprint:
            raise ConflictError(
                "Idempotency-Key was already used with a different request body",
                code="idempotency_conflict",
            )
        return existing.response_status, existing.response_body

    def _store_idempotency(
        self,
        *,
        workspace_id: str,
        key: str,
        endpoint: str,
        fingerprint: str,
        status_code: int,
        body: dict,
    ) -> None:
        self.repo.add(
            IdempotencyKey(
                workspace_id=workspace_id,
                key=key,
                endpoint=endpoint,
                request_hash=fingerprint,
                response_status=status_code,
                response_body=body,
            )
        )

    async def _commit_with_idempotency(
        self, workspace_id: str, key: Optional[str]
    ) -> Optional[Tuple[int, dict]]:
        """Commit the unit of work.

        If a concurrent request already inserted the same idempotency key, the
        unique constraint fails: we roll back (discarding our duplicate write)
        and replay the stored response instead.
        """
        try:
            await self.session.commit()
            return None
        except IntegrityError:
            await self.session.rollback()
            if key:
                existing = await self.repo.get_idempotency(workspace_id, key)
                if existing is not None:
                    return existing.response_status, existing.response_body
            raise

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #
    async def create(
        self,
        workspace_id: str,
        principal: Principal,
        payload: CreateApprovalRequestIn,
        idempotency_key: Optional[str],
    ) -> Tuple[int, dict]:
        fingerprint = _fingerprint(payload.model_dump(mode="json"))
        replay = await self._replay(workspace_id, idempotency_key, fingerprint)
        if replay is not None:
            return replay

        model = ApprovalRequest(
            id=_new_request_id(),
            workspace_id=workspace_id,
            source_type=payload.source_type.value,
            source_id=payload.source_id,
            title=payload.title,
            description=payload.description,
            reviewer_user_ids=payload.reviewer_user_ids,
            status=Status.pending.value,
            created_by=principal.user_id,
        )
        self.repo.add(model)
        await self.session.flush()

        events.record_audit(
            self.repo,
            workspace_id=workspace_id,
            request_id=model.id,
            action="created",
            actor_user_id=principal.user_id,
            summary={"status": Status.pending.value},
        )
        events.emit_event(
            self.repo,
            workspace_id=workspace_id,
            aggregate_id=model.id,
            event_type="approval_request.created",
            payload=_safe_event_payload(model),
        )

        status_code, body = 201, _body(model)
        if idempotency_key:
            self._store_idempotency(
                workspace_id=workspace_id,
                key=idempotency_key,
                endpoint="create",
                fingerprint=fingerprint,
                status_code=status_code,
                body=body,
            )
        replay = await self._commit_with_idempotency(workspace_id, idempotency_key)
        return replay if replay is not None else (status_code, body)

    async def decide(
        self,
        workspace_id: str,
        principal: Principal,
        request_id: str,
        action: str,
        payload,
        idempotency_key: Optional[str],
    ) -> Tuple[int, dict]:
        target = _DECISION_TARGET[action]
        fingerprint = _fingerprint(
            {"action": action, "body": payload.model_dump(mode="json")}
        )
        replay = await self._replay(workspace_id, idempotency_key, fingerprint)
        if replay is not None:
            return replay

        model = await self.repo.get(workspace_id, request_id, for_update=True)
        if model is None:
            raise NotFoundError("Approval request not found")

        current = Status(model.status)

        if current == target:
            # Re-applying the same terminal decision is idempotent.
            return 200, _body(model)

        if current in FINAL_STATUSES:
            raise ConflictError(
                f"Request is already {current.value} and cannot become {target.value}",
                code="invalid_transition",
            )

        # current is pending -> apply the decision.
        model.status = target.value
        model.decided_by = principal.user_id
        model.decided_at = _now()
        if isinstance(payload, ApproveIn):
            model.decision_comment = payload.comment
        elif isinstance(payload, (RejectIn, CancelIn)):
            model.decision_reason = payload.reason
        await self.session.flush()
        # `updated_at` uses a server-side onupdate; refresh so reading it back
        # does not trigger a lazy (sync) load in this async context.
        await self.session.refresh(model)

        events.record_audit(
            self.repo,
            workspace_id=workspace_id,
            request_id=model.id,
            action=action,
            actor_user_id=principal.user_id,
            summary={"from": current.value, "to": target.value},
        )
        events.emit_event(
            self.repo,
            workspace_id=workspace_id,
            aggregate_id=model.id,
            event_type=f"approval_request.{target.value}",
            payload=_safe_event_payload(model),
        )

        status_code, body = 200, _body(model)
        if idempotency_key:
            self._store_idempotency(
                workspace_id=workspace_id,
                key=idempotency_key,
                endpoint=action,
                fingerprint=fingerprint,
                status_code=status_code,
                body=body,
            )
        replay = await self._commit_with_idempotency(workspace_id, idempotency_key)
        return replay if replay is not None else (status_code, body)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    async def get(self, workspace_id: str, request_id: str) -> ApprovalRequestOut:
        model = await self.repo.get(workspace_id, request_id)
        if model is None:
            raise NotFoundError("Approval request not found")
        return to_out(model)

    async def list(
        self,
        workspace_id: str,
        status: Optional[str],
        limit: int,
        offset: int,
    ) -> ApprovalRequestListOut:
        rows = await self.repo.list(workspace_id, status, limit, offset)
        items = [to_out(r) for r in rows]
        return ApprovalRequestListOut(items=items, count=len(items))
