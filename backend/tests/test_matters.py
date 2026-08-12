"""Tests for /api/v1/matters (BE2): case workspaces, visibility, attachments."""
from __future__ import annotations

import asyncio

from app.main import app


def _run(coro):
    return asyncio.run(coro)


def _set_tier(chambers_id: str, tier: str) -> None:
    _run(app.state.chambers_registry.set_tier(chambers_id, tier))


def _seed_document(document_id: str, user_id: str) -> None:
    _run(app.state.document_registry.create_document({
        "document_id": document_id,
        "user_id": user_id,
        "document_name": f"{document_id}.pdf",
        "source_type": "pdf",
        "page_count": 1,
        "chunk_count": 1,
        "file_size_bytes": 10,
        "matter_id": None,
        "uploaded_at": "2026-01-01T00:00:00+00:00",
    }))


def test_create_matter_defaults(client) -> None:
    res = client.post("/api/v1/matters", json={"title": "Acme v. Beta", "practice_area": "litigation"})
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Acme v. Beta"
    assert data["practice_area"] == "LITIGATION"      # uppercased
    assert data["status"] == "OPEN"
    assert data["chambers_id"] is None                # personal matter


def test_create_matter_rejects_bad_practice_area(client) -> None:
    res = client.post("/api/v1/matters", json={"title": "X", "practice_area": "SORCERY"})
    assert res.status_code == 422


def test_create_matter_energy_practice_area(client) -> None:
    # ENERGY is in the plan's contract; make sure it's accepted.
    res = client.post("/api/v1/matters", json={"title": "Oil Block", "practice_area": "ENERGY"})
    assert res.status_code == 201


def test_create_matter_under_chambers_requires_membership(client, as_user) -> None:
    as_user("firm-owner")
    cid = client.post("/api/v1/chambers", json={"name": "Firm"}).json()["chambers_id"]

    as_user("stranger")
    res = client.post("/api/v1/matters", json={"title": "Sneaky", "chambers_id": cid})
    assert res.status_code == 403


def test_matter_visibility_creator_vs_stranger(client, as_user) -> None:
    as_user("author")
    mid = client.post("/api/v1/matters", json={"title": "Mine"}).json()["matter_id"]

    as_user("nobody")
    assert client.get(f"/api/v1/matters/{mid}").status_code == 404       # not leaked
    assert client.patch(f"/api/v1/matters/{mid}", json={"title": "hax"}).status_code == 404

    as_user("author")
    assert client.get(f"/api/v1/matters/{mid}").status_code == 200


def test_principal_sees_all_chambers_matters(client, as_user) -> None:
    as_user("boss")
    created = client.post("/api/v1/chambers", json={"name": "BigLaw"}).json()
    cid, invite = created["chambers_id"], created["invite_code"]
    _set_tier(cid, "STARTER")

    as_user("junior")
    client.post("/api/v1/chambers/join", json={"invite_code": invite})
    junior_matter = client.post(
        "/api/v1/matters", json={"title": "Junior's Case", "chambers_id": cid}
    ).json()["matter_id"]

    # The principal sees the junior's chambers matter in their list...
    as_user("boss")
    ids = {m["matter_id"] for m in client.get("/api/v1/matters").json()["matters"]}
    assert junior_matter in ids
    # ...and can open it (elevated role grants access even though they're not the creator).
    assert client.get(f"/api/v1/matters/{junior_matter}").status_code == 200


def test_matter_workspace_shape(client) -> None:
    mid = client.post("/api/v1/matters", json={"title": "Workspace"}).json()["matter_id"]
    body = client.get(f"/api/v1/matters/{mid}").json()
    assert set(body.keys()) == {"matter", "documents", "chats"}
    assert body["documents"] == []
    assert body["chats"] == []


def test_archive_matter_is_reversible_status_change(client) -> None:
    mid = client.post("/api/v1/matters", json={"title": "To Archive"}).json()["matter_id"]
    res = client.delete(f"/api/v1/matters/{mid}")
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"
    # Still visible to its creator (archive != destroy).
    assert client.get(f"/api/v1/matters/{mid}").json()["matter"]["status"] == "ARCHIVED"


def test_attach_and_detach_documents(client) -> None:
    mid = client.post("/api/v1/matters", json={"title": "Docs Case"}).json()["matter_id"]
    _seed_document("doc-mine", "test-user-1")
    _seed_document("doc-theirs", "someone-else")

    res = client.post(
        f"/api/v1/matters/{mid}/documents",
        json={"document_ids": ["doc-mine", "doc-theirs"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["attached"] == ["doc-mine"]        # only owned docs attach
    assert body["skipped"] == ["doc-theirs"]

    workspace = client.get(f"/api/v1/matters/{mid}").json()
    assert [d["document_id"] for d in workspace["documents"]] == ["doc-mine"]

    # Detach.
    assert client.delete(f"/api/v1/matters/{mid}/documents/doc-mine").status_code == 200
    assert client.get(f"/api/v1/matters/{mid}").json()["documents"] == []
    # Detaching an unknown doc 404s.
    assert client.delete(f"/api/v1/matters/{mid}/documents/ghost").status_code == 404


def test_attach_and_detach_chats(client) -> None:
    mid = client.post("/api/v1/matters", json={"title": "Chats Case"}).json()["matter_id"]
    chat_id = client.post("/api/v1/chats", json={"title": "Research"}).json()["chat_id"]

    res = client.post(f"/api/v1/matters/{mid}/chats", json={"chat_ids": [chat_id]})
    assert res.status_code == 200
    assert res.json()["attached"] == [chat_id]

    workspace = client.get(f"/api/v1/matters/{mid}").json()
    assert [c["chat_id"] for c in workspace["chats"]] == [chat_id]

    assert client.delete(f"/api/v1/matters/{mid}/chats/{chat_id}").status_code == 200
    assert client.get(f"/api/v1/matters/{mid}").json()["chats"] == []


def test_matters_require_auth(raw_client) -> None:
    assert raw_client.get("/api/v1/matters").status_code == 401
