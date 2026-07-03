from __future__ import annotations

from sqlalchemy import select

from app.models import ApprovalRequest, OutboxEvent

from .conftest import auth_headers

BASE = "/api/v1/workspaces/ws_1/approval-requests"
SAMPLE = {
    "sourceType": "publication",
    "sourceId": "pub_9",
    "title": "Draft",
    "reviewerUserIds": ["usr_2"],
}


async def test_repeated_create_with_same_key_is_deduplicated(client, sessionmaker):
    headers = auth_headers()
    headers["Idempotency-Key"] = "key-123"

    first = await client.post(BASE, json=SAMPLE, headers=headers)
    second = await client.post(BASE, json=SAMPLE, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    # Exactly one row persisted.
    async with sessionmaker() as session:
        rows = (await session.execute(select(ApprovalRequest))).scalars().all()
    assert len(rows) == 1


async def test_same_key_different_body_conflicts(client):
    headers = auth_headers()
    headers["Idempotency-Key"] = "key-abc"

    await client.post(BASE, json=SAMPLE, headers=headers)
    other = dict(SAMPLE, title="Changed")
    resp = await client.post(BASE, json=other, headers=headers)

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "idempotency_conflict"


async def test_decision_is_idempotent_with_key(client):
    rid = (await client.post(BASE, json=SAMPLE, headers=auth_headers())).json()["id"]

    headers = auth_headers()
    headers["Idempotency-Key"] = "decide-1"
    first = await client.post(
        f"{BASE}/{rid}/approve", json={"comment": "ok"}, headers=headers
    )
    second = await client.post(
        f"{BASE}/{rid}/approve", json={"comment": "ok"}, headers=headers
    )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


async def test_outbox_event_written_on_create(client, sessionmaker):
    await client.post(BASE, json=SAMPLE, headers=auth_headers())
    async with sessionmaker() as session:
        events = (await session.execute(select(OutboxEvent))).scalars().all()
    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "approval_request.created"
    # Safe payload only: no free-text / secret-bearing fields.
    assert "title" not in ev.payload
    assert "description" not in ev.payload
    assert ev.payload["id"].startswith("areq_")
