from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import (
    ACTION_CANCEL,
    ACTION_CREATE,
    ACTION_DECIDE,
    ACTION_READ,
    Principal,
    require_action,
)
from ..db import get_session
from ..models import Status
from ..schemas import (
    ApprovalRequestListOut,
    ApprovalRequestOut,
    ApproveIn,
    CancelIn,
    CreateApprovalRequestIn,
    RejectIn,
)
from ..service import ApprovalService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/approval-requests",
    tags=["approval-requests"],
)


def _idempotency_key(
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")
) -> Optional[str]:
    return idempotency_key


@router.post("", status_code=201, response_model=ApprovalRequestOut)
async def create_request(
    payload: CreateApprovalRequestIn,
    workspace_id: str = Path(...),
    principal: Principal = Depends(require_action(ACTION_CREATE)),
    idempotency_key: Optional[str] = Depends(_idempotency_key),
    session: AsyncSession = Depends(get_session),
):
    service = ApprovalService(session)
    status_code, body = await service.create(
        workspace_id, principal, payload, idempotency_key
    )
    return JSONResponse(status_code=status_code, content=body)


@router.get("", response_model=ApprovalRequestListOut)
async def list_requests(
    workspace_id: str = Path(...),
    status: Optional[Status] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_action(ACTION_READ)),
    session: AsyncSession = Depends(get_session),
):
    service = ApprovalService(session)
    status_value = status.value if status else None
    return await service.list(workspace_id, status_value, limit, offset)


@router.get("/{request_id}", response_model=ApprovalRequestOut)
async def get_request(
    workspace_id: str = Path(...),
    request_id: str = Path(...),
    principal: Principal = Depends(require_action(ACTION_READ)),
    session: AsyncSession = Depends(get_session),
):
    service = ApprovalService(session)
    return await service.get(workspace_id, request_id)


@router.post("/{request_id}/approve", response_model=ApprovalRequestOut)
async def approve_request(
    workspace_id: str = Path(...),
    request_id: str = Path(...),
    payload: ApproveIn = ApproveIn(),
    principal: Principal = Depends(require_action(ACTION_DECIDE)),
    idempotency_key: Optional[str] = Depends(_idempotency_key),
    session: AsyncSession = Depends(get_session),
):
    service = ApprovalService(session)
    status_code, body = await service.decide(
        workspace_id, principal, request_id, "approve", payload, idempotency_key
    )
    return JSONResponse(status_code=status_code, content=body)


@router.post("/{request_id}/reject", response_model=ApprovalRequestOut)
async def reject_request(
    payload: RejectIn,
    workspace_id: str = Path(...),
    request_id: str = Path(...),
    principal: Principal = Depends(require_action(ACTION_DECIDE)),
    idempotency_key: Optional[str] = Depends(_idempotency_key),
    session: AsyncSession = Depends(get_session),
):
    service = ApprovalService(session)
    status_code, body = await service.decide(
        workspace_id, principal, request_id, "reject", payload, idempotency_key
    )
    return JSONResponse(status_code=status_code, content=body)


@router.post("/{request_id}/cancel", response_model=ApprovalRequestOut)
async def cancel_request(
    payload: CancelIn,
    workspace_id: str = Path(...),
    request_id: str = Path(...),
    principal: Principal = Depends(require_action(ACTION_CANCEL)),
    idempotency_key: Optional[str] = Depends(_idempotency_key),
    session: AsyncSession = Depends(get_session),
):
    service = ApprovalService(session)
    status_code, body = await service.decide(
        workspace_id, principal, request_id, "cancel", payload, idempotency_key
    )
    return JSONResponse(status_code=status_code, content=body)
