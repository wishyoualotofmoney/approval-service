from __future__ import annotations

from .conftest import auth_headers

SAMPLE = {
    "sourceType": "edit",
    "sourceId": "edit_1",
    "title": "Draft",
    "reviewerUserIds": [],
}


async def test_workspace_data_is_isolated(client):
    # Create in ws_1.
    resp = await client.post(
        "/api/v1/workspaces/ws_1/approval-requests",
        json=SAMPLE,
        headers=auth_headers(workspace_id="ws_1"),
    )
    rid = resp.json()["id"]

    # ws_2 must not see it in its list.
    listed = await client.get(
        "/api/v1/workspaces/ws_2/approval-requests",
        headers=auth_headers(workspace_id="ws_2"),
    )
    assert listed.json()["count"] == 0

    # ws_2 must not fetch it directly -> 404 (existence not leaked).
    fetched = await client.get(
        f"/api/v1/workspaces/ws_2/approval-requests/{rid}",
        headers=auth_headers(workspace_id="ws_2"),
    )
    assert fetched.status_code == 404


async def test_token_workspace_must_match_path(client):
    # Token is for ws_2 but path targets ws_1 -> forbidden.
    resp = await client.post(
        "/api/v1/workspaces/ws_1/approval-requests",
        json=SAMPLE,
        headers=auth_headers(workspace_id="ws_2"),
    )
    assert resp.status_code == 403
