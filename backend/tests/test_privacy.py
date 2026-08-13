"""Tests for /api/v1/privacy (BE2): NDPA policy statement + right-to-erasure."""
from __future__ import annotations


def test_policy_statement_is_public(raw_client) -> None:
    # No auth header — this endpoint must be reachable unauthenticated.
    res = raw_client.get("/api/v1/privacy/policy-statement")
    assert res.status_code == 200
    body = res.json()
    assert "NDPA" in body["regulation"]
    assert body["retention"]["erasure_endpoint"] == "/api/v1/privacy/delete-my-data"
    assert isinstance(body["data_subject_rights"], list)


def test_delete_my_data_purges_everything(client) -> None:
    # Seed a footprint: profile, a chat, and a chambers membership.
    client.get("/api/v1/me/profile")                       # creates a profile row
    client.post("/api/v1/chats", json={"title": "Case notes"})
    client.post("/api/v1/chambers", json={"name": "Solo Chambers"})

    res = client.post("/api/v1/privacy/delete-my-data")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["deleted"]["profile"] is True
    assert body["deleted"]["chats"] >= 1
    assert body["deleted"]["memberships"] >= 1

    # Chats are gone; profile is recreated fresh (not the old one).
    assert client.get("/api/v1/chats").json()["chats"] == []
    reborn = client.get("/api/v1/me/profile").json()
    assert reborn["chambers_id"] is None


def test_delete_my_data_requires_auth(raw_client) -> None:
    assert raw_client.post("/api/v1/privacy/delete-my-data").status_code == 401
