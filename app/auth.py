from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Set

from fastapi import Depends, Header, Path

from .errors import AuthError, ForbiddenError

# Actions understood by the service (see README auth section).
ACTION_READ = "approval:read"
ACTION_CREATE = "approval:create"
ACTION_DECIDE = "approval:decide"
ACTION_CANCEL = "approval:cancel"

ALL_ACTIONS = {ACTION_READ, ACTION_CREATE, ACTION_DECIDE, ACTION_CANCEL}


@dataclass
class Principal:
    workspace_id: str
    user_id: str
    actions: Set[str]


def get_principal(
    x_workspace_id: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
    x_actions: Optional[str] = Header(default=None),
) -> Principal:
    """Local auth stub.

    Credentials are passed as plain headers (no signature - stub only):
      X-Workspace-Id: ws_1
      X-User-Id:      usr_1
      X-Actions:      approval:read,approval:create,approval:decide,approval:cancel
    """
    if not x_workspace_id or not x_user_id:
        raise AuthError("Missing X-Workspace-Id or X-User-Id header")

    actions = {a.strip() for a in (x_actions or "").split(",") if a.strip()}
    unknown = actions - ALL_ACTIONS
    if unknown:
        raise AuthError(f"Unknown actions: {', '.join(sorted(unknown))}")

    return Principal(
        workspace_id=x_workspace_id, user_id=x_user_id, actions=actions
    )


def require_action(action: str):
    """Dependency factory: enforce path/token workspace match + required action.

    The workspace in the auth headers must match the {workspace_id} in the URL,
    and the principal must carry the required action - otherwise 403.
    """

    def _dep(
        workspace_id: str = Path(...),
        principal: Principal = Depends(get_principal),
    ) -> Principal:
        if principal.workspace_id != workspace_id:
            raise ForbiddenError(
                "Token workspace does not match the requested workspace"
            )
        if action not in principal.actions:
            raise ForbiddenError(f"Missing required action: {action}")
        return principal

    return _dep
