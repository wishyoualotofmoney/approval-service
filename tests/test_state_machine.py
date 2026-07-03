from __future__ import annotations

from .conftest import auth_headers

BASE = "/api/v1/workspaces/ws_1/approval-requests"

SAMPLE = {
    "sourceType": "scenario",
    "sourceId": "scn_1",
    "title": "Draft",
    "reviewerUserIds": ["usr_2"],
}


async def _create(client):
    resp = await client.post(BASE, json=SAMPLE, headers=auth_headers())
    return resp.json()["id"]


async def test_approve(client):
    rid = await _create(client)
    resp = await client.post(
        f"{BASE}/{rid}/approve", json={"comment": "Approved"}, headers=auth_headers()
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["decision"]["comment"] == "Approved"
    assert data["decision"]["decidedBy"] == "usr_1"
    assert data["decision"]["decidedAt"] is not None


async def test_approve_with_empty_body(client):
    rid = await _create(client)
    resp = await client.post(f"{BASE}/{rid}/approve", headers=auth_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


async def test_reject(client):
    rid = await _create(client)
    resp = await client.post(
        f"{BASE}/{rid}/reject",
        json={"reason": "Brand tone is wrong"},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["decision"]["reason"] == "Brand tone is wrong"


async def test_cancel(client):
    rid = await _create(client)
    resp = await client.post(
        f"{BASE}/{rid}/cancel",
        json={"reason": "Draft was removed"},
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_reject_requires_reason(client):
    rid = await _create(client)
    resp = await client.post(f"{BASE}/{rid}/reject", json={}, headers=auth_headers())
    assert resp.status_code == 422


async def test_no_transition_between_final_states(client):
    rid = await _create(client)
    await client.post(
        f"{BASE}/{rid}/approve", json={"comment": "ok"}, headers=auth_headers()
    )
    # Attempting a different terminal decision must conflict.
    resp = await client.post(
        f"{BASE}/{rid}/reject", json={"reason": "no"}, headers=auth_headers()
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "invalid_transition"


async def test_reapplying_same_decision_is_idempotent(client):
    rid = await _create(client)
    first = await client.post(
        f"{BASE}/{rid}/approve", json={"comment": "ok"}, headers=auth_headers()
    )
    second = await client.post(
        f"{BASE}/{rid}/approve", json={"comment": "different"}, headers=auth_headers()
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "approved"
