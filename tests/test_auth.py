from __future__ import annotations

from .conftest import auth_headers

BASE = "/api/v1/workspaces/ws_1/approval-requests"
SAMPLE = {"sourceType": "external", "sourceId": "x_1", "title": "T", "reviewerUserIds": []}


async def test_missing_credentials_is_401(client):
    resp = await client.post(BASE, json=SAMPLE)
    assert resp.status_code == 401


async def test_missing_action_is_403(client):
    # Read-only principal cannot create.
    resp = await client.post(
        BASE, json=SAMPLE, headers=auth_headers(actions="approval:read")
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


async def test_cancel_needs_cancel_action(client):
    created = await client.post(BASE, json=SAMPLE, headers=auth_headers())
    rid = created.json()["id"]
    # Principal with decide but not cancel.
    resp = await client.post(
        f"{BASE}/{rid}/cancel",
        json={"reason": "x"},
        headers=auth_headers(actions="approval:decide"),
    )
    assert resp.status_code == 403


async def test_unknown_action_rejected(client):
    resp = await client.post(
        BASE, json=SAMPLE, headers=auth_headers(actions="approval:destroy")
    )
    assert resp.status_code == 401
