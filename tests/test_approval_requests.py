from __future__ import annotations

from .conftest import auth_headers

BASE = "/api/v1/workspaces/ws_1/approval-requests"

SAMPLE = {
    "sourceType": "publication",
    "sourceId": "pub_123",
    "title": "Instagram reel draft",
    "description": "Needs final approval",
    "reviewerUserIds": ["usr_1", "usr_2"],
}


async def _create(client, body=None, headers=None):
    return await client.post(
        BASE, json=body or SAMPLE, headers=headers or auth_headers()
    )


async def test_create_returns_pending_request(client):
    resp = await _create(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("areq_")
    assert data["status"] == "pending"
    assert data["workspaceId"] == "ws_1"
    assert data["sourceType"] == "publication"
    assert data["reviewerUserIds"] == ["usr_1", "usr_2"]
    assert data["createdBy"] == "usr_1"
    assert data["decision"] is None


async def test_get_one(client):
    created = (await _create(client)).json()
    resp = await client.get(f"{BASE}/{created['id']}", headers=auth_headers())
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_missing_returns_404(client):
    resp = await client.get(f"{BASE}/areq_missing", headers=auth_headers())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_list(client):
    await _create(client)
    await _create(client)
    resp = await client.get(BASE, headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert len(body["items"]) == 2


async def test_list_filter_by_status(client):
    created = (await _create(client)).json()
    await client.post(
        f"{BASE}/{created['id']}/approve",
        json={"comment": "ok"},
        headers=auth_headers(),
    )
    await _create(client)  # a second, still-pending request

    resp = await client.get(f"{BASE}?status=approved", headers=auth_headers())
    assert resp.json()["count"] == 1
    assert resp.json()["items"][0]["status"] == "approved"


async def test_create_rejects_unknown_field(client):
    bad = dict(SAMPLE, providerUrl="https://cdn.example.com/secret.mp4")
    resp = await _create(client, body=bad)
    assert resp.status_code == 422


async def test_create_rejects_bad_source_type(client):
    bad = dict(SAMPLE, sourceType="video")
    resp = await _create(client, body=bad)
    assert resp.status_code == 422
