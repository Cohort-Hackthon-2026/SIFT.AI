"""Tests for GET /api/v1/audit (BE2): feature gate + role gate + chambers scoping."""
from __future__ import annotations

import asyncio

from app.main import app


def _run(coro):
    return asyncio.run(coro)


def _set_tier(chambers_id: str, tier: str) -> None:
    _run(app.state.chambers_registry.set_tier(chambers_id, tier))


def _seed_log(chambers_id: str, user_id: str, action: str = "CHAT_EXPORT") -> None:
    _run(app.state.audit_registry.record(user_id, action, chambers_id=chambers_id, detail={"k": "v"}))


def test_audit_requires_a_chambers_400(client) -> None:
    # A user with no chambers has no firm-wide trail to read.
    res = client.get("/api/v1/audit")
    assert res.status_code == 400


def test_audit_gated_by_plan_402_on_free(client) -> None:
    # Chambers exists but is FREE -> the audit_log feature is PRO+.
    client.post("/api/v1/chambers", json={"name": "Free Firm"})
    res = client.get("/api/v1/audit")
    assert res.status_code == 402
    assert res.json()["detail"]["upgrade_required"] == "PRO"


def test_audit_principal_on_pro_can_read(client) -> None:
    cid = client.post("/api/v1/chambers", json={"name": "Pro Firm"}).json()["chambers_id"]
    _set_tier(cid, "PRO")
    _seed_log(cid, "test-user-1")

    res = client.get("/api/v1/audit")
    assert res.status_code == 200
    body = res.json()
    assert body["chambers_id"] == cid
    assert body["tier"] == "PRO"
    assert body["count"] >= 1
    assert body["logs"][0]["action"] == "CHAT_EXPORT"


def test_audit_scoped_to_own_chambers_only(client, as_user) -> None:
    # Two PRO firms; each principal sees only their own firm's entries.
    as_user("boss-1")
    cid1 = client.post("/api/v1/chambers", json={"name": "Firm One"}).json()["chambers_id"]
    _set_tier(cid1, "PRO")
    _seed_log(cid1, "boss-1", action="MATTER_CREATE")

    as_user("boss-2")
    cid2 = client.post("/api/v1/chambers", json={"name": "Firm Two"}).json()["chambers_id"]
    _set_tier(cid2, "PRO")
    _seed_log(cid2, "boss-2", action="CHAT_EXPORT")

    actions = {log["action"] for log in client.get("/api/v1/audit").json()["logs"]}
    assert "CHAT_EXPORT" in actions            # firm two's own entry is visible
    assert "MATTER_CREATE" not in actions      # firm one's entry is not leaked


def test_audit_associate_forbidden_403(client, as_user) -> None:
    as_user("lead")
    created = client.post("/api/v1/chambers", json={"name": "Trail Firm"}).json()
    cid, invite = created["chambers_id"], created["invite_code"]
    _set_tier(cid, "PRO")

    as_user("worker")
    client.post("/api/v1/chambers/join", json={"invite_code": invite})
    # An associate is a member and on a PRO plan, but not leadership.
    res = client.get("/api/v1/audit")
    assert res.status_code == 403


def test_audit_partner_can_read(client, as_user) -> None:
    as_user("lead-2")
    created = client.post("/api/v1/chambers", json={"name": "Partner Firm"}).json()
    cid, invite = created["chambers_id"], created["invite_code"]
    _set_tier(cid, "PRO")

    as_user("partner-1")
    client.post("/api/v1/chambers/join", json={"invite_code": invite})

    as_user("lead-2")
    client.patch(f"/api/v1/chambers/{cid}/members/partner-1", json={"role": "PARTNER"})

    as_user("partner-1")
    assert client.get("/api/v1/audit").status_code == 200


def test_audit_requires_auth(raw_client) -> None:
    assert raw_client.get("/api/v1/audit").status_code == 401
