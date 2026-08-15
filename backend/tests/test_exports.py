"""Tests for POST /api/v1/chats/{chat_id}/export (BE2): rendering + tier gates + metering."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.main import app


def _run(coro):
    return asyncio.run(coro)


def _set_tier(chambers_id: str, tier: str) -> None:
    _run(app.state.chambers_registry.set_tier(chambers_id, tier))


def _seed_chat_with_messages(user_id: str, *, matter_id: str | None = None) -> str:
    """Create a chat owned by user_id with one Q/A turn, return its id."""
    chat = _run(app.state.chat_registry.create_chat(
        user_id=user_id, title="Contract dispute research", matter_id=matter_id,
    ))
    chat_id = chat["chat_id"]
    _run(app.state.chat_registry.add_message(chat_id, "user", "What did the SCN hold?"))
    _run(app.state.chat_registry.add_message(
        chat_id, "assistant",
        "The Supreme Court held the contract void.",
        {"internal_citations": [{"document_name": "Judgment.pdf", "page": 3}]},
    ))
    return chat_id


def test_export_pdf_on_free_returns_pdf_bytes(client) -> None:
    chat_id = _seed_chat_with_messages("test-user-1")
    res = client.post(f"/api/v1/chats/{chat_id}/export", json={"format": "PDF"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.headers["content-disposition"].startswith('attachment; filename="')
    assert res.content[:4] == b"%PDF"          # a real PDF, not an error page


def test_export_pdf_defaults_when_no_format(client) -> None:
    chat_id = _seed_chat_with_messages("test-user-1")
    res = client.post(f"/api/v1/chats/{chat_id}/export", json={})
    assert res.status_code == 200
    assert res.content[:4] == b"%PDF"


def test_export_meters_an_export_usage_event(client) -> None:
    chat_id = _seed_chat_with_messages("test-user-1")
    client.post(f"/api/v1/chats/{chat_id}/export", json={"format": "PDF"})
    # FREE user with no chambers -> usage is recorded against the user.
    summary = _run(app.state.billing_registry.usage_summary(user_id="test-user-1"))
    assert summary.get("EXPORT", 0) >= 1


def test_export_docx_blocked_on_free_but_allowed_on_starter(client, as_user) -> None:
    as_user("exporter")
    # Give this user a chambers so we can raise their tier.
    cid = client.post("/api/v1/chambers", json={"name": "Export Chambers"}).json()["chambers_id"]
    chat_id = _seed_chat_with_messages("exporter")

    # FREE -> DOCX is a paid format -> 402 with an upgrade hint.
    blocked = client.post(f"/api/v1/chats/{chat_id}/export", json={"format": "DOCX"})
    assert blocked.status_code == 402
    assert blocked.json()["detail"]["upgrade_required"] == "STARTER"

    # Upgrade the chambers -> DOCX now renders a real .docx (zip container).
    _set_tier(cid, "STARTER")
    ok = client.post(f"/api/v1/chats/{chat_id}/export", json={"format": "DOCX"})
    assert ok.status_code == 200
    assert ok.content[:4] == b"PK\x03\x04"       # zip magic == valid OOXML


def test_export_pptx_requires_pro(client, as_user) -> None:
    as_user("pptx-user")
    cid = client.post("/api/v1/chambers", json={"name": "Deck Chambers"}).json()["chambers_id"]
    chat_id = _seed_chat_with_messages("pptx-user")

    _set_tier(cid, "STARTER")
    assert client.post(f"/api/v1/chats/{chat_id}/export", json={"format": "PPTX"}).status_code == 402

    _set_tier(cid, "PRO")
    ok = client.post(f"/api/v1/chats/{chat_id}/export", json={"format": "PPTX"})
    assert ok.status_code == 200
    assert ok.content[:4] == b"PK\x03\x04"


def test_export_unsupported_format_422(client) -> None:
    chat_id = _seed_chat_with_messages("test-user-1")
    res = client.post(f"/api/v1/chats/{chat_id}/export", json={"format": "TXT"})
    assert res.status_code == 422


def test_export_unknown_chat_404(client) -> None:
    res = client.post("/api/v1/chats/does-not-exist/export", json={"format": "PDF"})
    assert res.status_code == 404


def test_export_other_users_chat_404(client, as_user) -> None:
    chat_id = _seed_chat_with_messages("owner-of-chat")
    as_user("thief")
    res = client.post(f"/api/v1/chats/{chat_id}/export", json={"format": "PDF"})
    assert res.status_code == 404          # ownership hidden as not-found


def test_export_requires_auth(raw_client) -> None:
    assert raw_client.post("/api/v1/chats/x/export", json={"format": "PDF"}).status_code == 401
