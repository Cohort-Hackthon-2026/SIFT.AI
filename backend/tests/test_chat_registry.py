"""Tests for ChatRegistry (InMemory and Postgres repositories)."""
from __future__ import annotations

import pytest

from app.db.chat_registry import InMemoryChatRegistry


@pytest.mark.asyncio
async def test_inmemory_chat_crud() -> None:
    registry = InMemoryChatRegistry()
    await registry.initialize()

    # Create chat
    chat = await registry.create_chat(
        user_id="usr-1",
        title="Lease Research",
        mode="STRICT",
        document_ids=["doc-1", "doc-2"],
    )
    assert chat["chat_id"] is not None
    assert chat["user_id"] == "usr-1"
    assert chat["title"] == "Lease Research"
    assert chat["mode"] == "STRICT"
    assert chat["document_ids"] == ["doc-1", "doc-2"]

    # List chats
    user_chats = await registry.list_chats("usr-1")
    assert len(user_chats) == 1
    assert user_chats[0]["chat_id"] == chat["chat_id"]

    # Other user gets empty list
    other_chats = await registry.list_chats("usr-2")
    assert len(other_chats) == 0

    # Get single chat
    fetched = await registry.get_chat(chat["chat_id"], user_id="usr-1")
    assert fetched is not None
    assert fetched["chat_id"] == chat["chat_id"]

    # Get single chat by wrong owner returns None
    wrong_owner = await registry.get_chat(chat["chat_id"], user_id="usr-2")
    assert wrong_owner is None

    # Update chat
    updated = await registry.update_chat(
        chat_id=chat["chat_id"],
        user_id="usr-1",
        title="Updated Lease Analysis",
        mode="ENHANCED",
        document_ids=["doc-1"],
    )
    assert updated is not None
    assert updated["title"] == "Updated Lease Analysis"
    assert updated["mode"] == "ENHANCED"
    assert updated["document_ids"] == ["doc-1"]

    # Messages
    user_msg = await registry.add_message(
        chat_id=chat["chat_id"],
        role="user",
        content="What is section 4?",
    )
    assert user_msg["role"] == "user"
    assert user_msg["content"] == "What is section 4?"

    asst_msg = await registry.add_message(
        chat_id=chat["chat_id"],
        role="assistant",
        content="Section 4 requires 30 days notice.",
        metadata={"citations": ["doc-1"]},
    )
    assert asst_msg["role"] == "assistant"
    assert asst_msg["metadata"] == {"citations": ["doc-1"]}

    # List messages
    msgs = await registry.list_messages(chat["chat_id"], user_id="usr-1")
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"

    # Delete chat
    deleted = await registry.delete_chat(chat["chat_id"], user_id="usr-1")
    assert deleted is True
    assert await registry.get_chat(chat["chat_id"]) is None
    assert len(await registry.list_messages(chat["chat_id"])) == 0
