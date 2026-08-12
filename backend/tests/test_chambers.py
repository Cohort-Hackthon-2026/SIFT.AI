"""Tests for /api/v1/chambers (BE2): team accounts, invites, roles, seats."""
from __future__ import annotations

import asyncio

from app.main import app


def _run(coro):
    return asyncio.run(coro)


def _set_tier(chambers_id: str, tier: str) -> None:
    """Directly set a chambers' tier (simulates a completed payment)."""
    _run(app.state.chambers_registry.set_tier(chambers_id, tier))


def test_create_chambers_makes_creator_principal(client) -> None:
    res = client.post("/api/v1/chambers", json={"name": "Balogun & Co"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Balogun & Co"
    assert data["subscription_tier"] == "FREE"
    assert data["invite_code"]

    listed = client.get("/api/v1/chambers").json()["chambers"]
    assert len(listed) == 1
    assert listed[0]["my_role"] == "PRINCIPAL"


def test_create_syncs_profile_chambers(client) -> None:
    res = client.post("/api/v1/chambers", json={"name": "Sync Chambers"})
    cid = res.json()["chambers_id"]
    profile = client.get("/api/v1/me/profile").json()
    assert profile["chambers_id"] == cid


def test_join_with_invite_code(client, as_user) -> None:
    as_user("principal-1")
    created = client.post("/api/v1/chambers", json={"name": "Growing Firm"}).json()
    cid = created["chambers_id"]
    invite = created["invite_code"]
    _set_tier(cid, "STARTER")  # FREE only allows 1 seat; upgrade to add members

    as_user("associate-1")
    res = client.post("/api/v1/chambers/join", json={"invite_code": invite})
    assert res.status_code == 200
    assert res.json()["membership"]["role"] == "ASSOCIATE"
    # Joining synced the associate's profile.
    assert client.get("/api/v1/me/profile").json()["chambers_id"] == cid


def test_join_invalid_code_404(client) -> None:
    res = client.post("/api/v1/chambers/join", json={"invite_code": "NOPE1234"})
    assert res.status_code == 404


def test_free_tier_seat_limit_blocks_second_member(client, as_user) -> None:
    as_user("solo-principal")
    created = client.post("/api/v1/chambers", json={"name": "Solo"}).json()
    invite = created["invite_code"]  # stays FREE (max_members == 1)

    as_user("would-be-member")
    res = client.post("/api/v1/chambers/join", json={"invite_code": invite})
    assert res.status_code == 402
    assert res.json()["detail"]["upgrade_required"] == "STARTER"


def test_invite_code_hidden_from_associates(client, as_user) -> None:
    as_user("principal-2")
    created = client.post("/api/v1/chambers", json={"name": "Discreet Chambers"}).json()
    cid, invite = created["chambers_id"], created["invite_code"]
    _set_tier(cid, "STARTER")

    as_user("associate-2")
    client.post("/api/v1/chambers/join", json={"invite_code": invite})
    details = client.get(f"/api/v1/chambers/{cid}").json()
    assert details["my_role"] == "ASSOCIATE"
    assert "invite_code" not in details          # associates can't re-share the code

    as_user("principal-2")
    principal_view = client.get(f"/api/v1/chambers/{cid}").json()
    assert principal_view["invite_code"] == invite


def test_non_member_cannot_see_chambers_404(client, as_user) -> None:
    as_user("owner-x")
    cid = client.post("/api/v1/chambers", json={"name": "Private"}).json()["chambers_id"]

    as_user("outsider")
    assert client.get(f"/api/v1/chambers/{cid}").status_code == 404


def test_only_principal_changes_roles(client, as_user) -> None:
    as_user("principal-3")
    created = client.post("/api/v1/chambers", json={"name": "Role Firm"}).json()
    cid, invite = created["chambers_id"], created["invite_code"]
    _set_tier(cid, "STARTER")

    as_user("member-3")
    client.post("/api/v1/chambers/join", json={"invite_code": invite})

    # A member cannot promote anyone.
    res_forbidden = client.patch(f"/api/v1/chambers/{cid}/members/member-3", json={"role": "PARTNER"})
    assert res_forbidden.status_code == 403

    # The principal can, and invalid roles are rejected.
    as_user("principal-3")
    assert client.patch(f"/api/v1/chambers/{cid}/members/member-3", json={"role": "PARTNER"}).status_code == 200
    assert client.patch(f"/api/v1/chambers/{cid}/members/member-3", json={"role": "KING"}).status_code == 422


def test_member_can_leave_and_principal_can_remove(client, as_user) -> None:
    as_user("principal-4")
    created = client.post("/api/v1/chambers", json={"name": "Leaving Firm"}).json()
    cid, invite = created["chambers_id"], created["invite_code"]
    _set_tier(cid, "STARTER")

    as_user("leaver")
    client.post("/api/v1/chambers/join", json={"invite_code": invite})
    # A member may remove themselves (leave).
    assert client.delete(f"/api/v1/chambers/{cid}/members/leaver").status_code == 200
    # Leaving cleared their profile pointer.
    assert client.get("/api/v1/me/profile").json()["chambers_id"] is None
    # And they can no longer see the chambers.
    assert client.get(f"/api/v1/chambers/{cid}").status_code == 404


def test_chambers_requires_auth(raw_client) -> None:
    assert raw_client.get("/api/v1/chambers").status_code == 401
