"""Tests for /api/v1/me/profile (BE2)."""
from __future__ import annotations


def test_get_profile_lazily_creates_default(client) -> None:
    res = client.get("/api/v1/me/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "test-user-1"
    assert data["role"] == "ASSOCIATE"          # sensible default
    assert data["default_jurisdiction"] == "NG"
    assert data["chambers_id"] is None


def test_update_profile_fields(client) -> None:
    res = client.put(
        "/api/v1/me/profile",
        json={"role": "principal", "nba_number": "SCN123456", "default_jurisdiction": "ng"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "PRINCIPAL"           # uppercased
    assert data["nba_number"] == "SCN123456"
    assert data["default_jurisdiction"] == "NG"


def test_update_profile_rejects_invalid_role(client) -> None:
    res = client.put("/api/v1/me/profile", json={"role": "WIZARD"})
    assert res.status_code == 422


def test_profile_is_per_user(client, as_user) -> None:
    as_user("user-a")
    client.put("/api/v1/me/profile", json={"nba_number": "AAA-1"})

    as_user("user-b")
    res_b = client.get("/api/v1/me/profile")
    assert res_b.json()["nba_number"] is None    # b sees a fresh profile, not a's

    as_user("user-a")
    res_a = client.get("/api/v1/me/profile")
    assert res_a.json()["nba_number"] == "AAA-1"


def test_profile_requires_auth(raw_client) -> None:
    assert raw_client.get("/api/v1/me/profile").status_code == 401
