"""Tests for REST endpoints under /api/v1/chats."""
from __future__ import annotations


def test_create_and_get_chat(client) -> None:
    # 1. Create a chat session
    create_resp = client.post(
        "/api/v1/chats",
        json={
            "title": "Contract Analysis",
            "mode": "ENHANCED",
            "document_ids": ["doc-100", "doc-200"],
        },
    )
    assert create_resp.status_code == 201
    chat_data = create_resp.json()
    chat_id = chat_data["chat_id"]
    assert chat_data["title"] == "Contract Analysis"
    assert chat_data["mode"] == "ENHANCED"
    assert chat_data["document_ids"] == ["doc-100", "doc-200"]

    # 2. Get chat details
    get_resp = client.get(f"/api/v1/chats/{chat_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["chat_id"] == chat_id


def test_list_chats_user_isolation(client, as_user) -> None:
    # User A creates a chat
    as_user("user-a")
    res_a = client.post("/api/v1/chats", json={"title": "User A Chat"})
    chat_id_a = res_a.json()["chat_id"]

    # User B creates a chat
    as_user("user-b")
    res_b = client.post("/api/v1/chats", json={"title": "User B Chat"})
    chat_id_b = res_b.json()["chat_id"]

    # User A lists chats -> sees only User A Chat
    as_user("user-a")
    list_a = client.get("/api/v1/chats").json()["chats"]
    assert len(list_a) == 1
    assert list_a[0]["chat_id"] == chat_id_a

    # User A cannot access User B's chat (404)
    get_other = client.get(f"/api/v1/chats/{chat_id_b}")
    assert get_other.status_code == 404


def test_update_chat_session(client) -> None:
    res = client.post("/api/v1/chats", json={"title": "Original Title"})
    chat_id = res.json()["chat_id"]

    patch_resp = client.patch(
        f"/api/v1/chats/{chat_id}",
        json={"title": "New Updated Title", "mode": "ENHANCED"},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["title"] == "New Updated Title"
    assert data["mode"] == "ENHANCED"


def test_delete_chat_session(client) -> None:
    res = client.post("/api/v1/chats", json={"title": "ToDelete"})
    chat_id = res.json()["chat_id"]

    del_resp = client.delete(f"/api/v1/chats/{chat_id}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"chat_id": chat_id, "deleted": True}

    get_resp = client.get(f"/api/v1/chats/{chat_id}")
    assert get_resp.status_code == 404


def test_list_messages_returns_empty_for_new_chat(client) -> None:
    res = client.post("/api/v1/chats", json={"title": "New Chat"})
    chat_id = res.json()["chat_id"]

    msg_resp = client.get(f"/api/v1/chats/{chat_id}/messages")
    assert msg_resp.status_code == 200
    assert msg_resp.json()["messages"] == []


def test_unauthenticated_request_returns_401(raw_client) -> None:
    res = raw_client.get("/api/v1/chats")
    assert res.status_code == 401
