from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)


class ChatRegistryProtocol(Protocol):
    """Repository protocol for managing chat sessions and message histories.

    Backed by PostgreSQL (Neon) when DATABASE_URL is configured, or an
    in-memory dictionary fallback for local development.
    """

    async def initialize(self) -> None: ...

    async def create_chat(
        self,
        user_id: str,
        title: str = "New Research Chat",
        mode: str = "STRICT",
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]: ...

    async def list_chats(self, user_id: str) -> list[dict[str, Any]]: ...

    async def get_chat(self, chat_id: str, user_id: str | None = None) -> dict[str, Any] | None: ...

    async def update_chat(
        self,
        chat_id: str,
        user_id: str,
        title: str | None = None,
        mode: str | None = None,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any] | None: ...

    async def delete_chat(self, chat_id: str, user_id: str) -> bool: ...

    async def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def list_messages(self, chat_id: str, user_id: str | None = None) -> list[dict[str, Any]]: ...


@dataclass
class InMemoryChatRegistry:
    """Fallback registry used when DATABASE_URL is not configured/reachable."""

    _chats: dict[str, dict[str, Any]] = field(default_factory=dict)
    _messages: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    async def initialize(self) -> None:
        return

    async def create_chat(
        self,
        user_id: str,
        title: str = "New Research Chat",
        mode: str = "STRICT",
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        chat_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "chat_id": chat_id,
            "user_id": user_id,
            "title": title or "New Research Chat",
            "mode": mode.upper() if mode else "STRICT",
            "document_ids": document_ids or [],
            "created_at": now,
            "updated_at": now,
        }
        self._chats[chat_id] = record
        self._messages[chat_id] = []
        return record

    async def list_chats(self, user_id: str) -> list[dict[str, Any]]:
        chats = [c for c in self._chats.values() if c.get("user_id") == user_id]
        return sorted(chats, key=lambda c: c["updated_at"], reverse=True)

    async def get_chat(self, chat_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        chat = self._chats.get(chat_id)
        if chat is None:
            return None
        if user_id is not None and chat.get("user_id") != user_id:
            return None
        return chat

    async def update_chat(
        self,
        chat_id: str,
        user_id: str,
        title: str | None = None,
        mode: str | None = None,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        chat = await self.get_chat(chat_id, user_id=user_id)
        if not chat:
            return None

        if title is not None:
            chat["title"] = title
        if mode is not None:
            chat["mode"] = mode.upper()
        if document_ids is not None:
            chat["document_ids"] = document_ids

        chat["updated_at"] = datetime.now(timezone.utc).isoformat()
        return chat

    async def delete_chat(self, chat_id: str, user_id: str) -> bool:
        chat = await self.get_chat(chat_id, user_id=user_id)
        if not chat:
            return False
        self._chats.pop(chat_id, None)
        self._messages.pop(chat_id, None)
        return True

    async def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "message_id": message_id,
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": now,
        }
        if chat_id not in self._messages:
            self._messages[chat_id] = []
        self._messages[chat_id].append(record)

        if chat_id in self._chats:
            self._chats[chat_id]["updated_at"] = now
        return record

    async def list_messages(self, chat_id: str, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id is not None:
            chat = await self.get_chat(chat_id, user_id=user_id)
            if not chat:
                return []
        messages = self._messages.get(chat_id, [])
        return sorted(messages, key=lambda m: m["created_at"])


class PostgresChatRegistry:
    """PostgreSQL-backed chat repository using asyncpg."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

            # asyncpg doesn't understand channel_binding=require or sslmode=require
            # query params — it uses native ssl kwarg instead. Strip them out and
            # pass ssl="require" directly so Neon Postgres connections work.
            parsed = urlparse(self._database_url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            # Collect SSL mode before stripping
            ssl_mode = params.pop("sslmode", [None])[0]
            # asyncpg has no concept of channel_binding — remove it silently
            params.pop("channel_binding", None)
            clean_query = urlencode({k: v[0] for k, v in params.items()})
            clean_url = urlunparse(parsed._replace(query=clean_query))

            ssl_arg = "require" if ssl_mode == "require" else None
            self._pool = await asyncpg.create_pool(clean_url, ssl=ssl_arg)
        return self._pool

    async def initialize(self) -> None:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        mode TEXT NOT NULL DEFAULT 'STRICT',
                        document_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);

                    CREATE TABLE IF NOT EXISTS messages (
                        message_id TEXT PRIMARY KEY,
                        chat_id TEXT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
                """)
            logger.info("PostgresChatRegistry: `chats` and `messages` tables verified/created.")
        except Exception as exc:
            logger.error("PostgresChatRegistry initialization failed: %s", exc)
            raise

    async def create_chat(
        self,
        user_id: str,
        title: str = "New Research Chat",
        mode: str = "STRICT",
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        chat_id = str(uuid4())
        now = datetime.now(timezone.utc)
        doc_json = json.dumps(document_ids or [])
        mode_val = mode.upper() if mode else "STRICT"

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO chats (chat_id, user_id, title, mode, document_ids, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $6)
                RETURNING chat_id, user_id, title, mode, document_ids, created_at, updated_at
                """,
                chat_id,
                user_id,
                title,
                mode_val,
                doc_json,
                now,
            )
            return self._row_to_chat(row)

    async def list_chats(self, user_id: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT chat_id, user_id, title, mode, document_ids, created_at, updated_at
                FROM chats
                WHERE user_id = $1
                ORDER BY updated_at DESC
                """,
                user_id,
            )
            return [self._row_to_chat(row) for row in rows]

    async def get_chat(self, chat_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if user_id is not None:
                row = await conn.fetchrow(
                    """
                    SELECT chat_id, user_id, title, mode, document_ids, created_at, updated_at
                    FROM chats
                    WHERE chat_id = $1 AND user_id = $2
                    """,
                    chat_id,
                    user_id,
                )
            else:
                row = await conn.fetchrow(
                    """
                    SELECT chat_id, user_id, title, mode, document_ids, created_at, updated_at
                    FROM chats
                    WHERE chat_id = $1
                    """,
                    chat_id,
                )
            return self._row_to_chat(row) if row else None

    async def update_chat(
        self,
        chat_id: str,
        user_id: str,
        title: str | None = None,
        mode: str | None = None,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        current = await self.get_chat(chat_id, user_id=user_id)
        if not current:
            return None

        new_title = title if title is not None else current["title"]
        new_mode = mode.upper() if mode is not None else current["mode"]
        new_docs = json.dumps(document_ids if document_ids is not None else current["document_ids"])
        now = datetime.now(timezone.utc)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE chats
                SET title = $1, mode = $2, document_ids = $3::jsonb, updated_at = $4
                WHERE chat_id = $5 AND user_id = $6
                RETURNING chat_id, user_id, title, mode, document_ids, created_at, updated_at
                """,
                new_title,
                new_mode,
                new_docs,
                now,
                chat_id,
                user_id,
            )
            return self._row_to_chat(row) if row else None

    async def delete_chat(self, chat_id: str, user_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM chats WHERE chat_id = $1 AND user_id = $2",
                chat_id,
                user_id,
            )
            return result.endswith("1")

    async def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid4())
        now = datetime.now(timezone.utc)
        meta_json = json.dumps(metadata or {})

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO messages (message_id, chat_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                RETURNING message_id, chat_id, role, content, metadata, created_at
                """,
                message_id,
                chat_id,
                role,
                content,
                meta_json,
                now,
            )
            # Touch chat updated_at
            await conn.execute(
                "UPDATE chats SET updated_at = $1 WHERE chat_id = $2",
                now,
                chat_id,
            )
            return self._row_to_message(row)

    async def list_messages(self, chat_id: str, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id is not None:
            chat = await self.get_chat(chat_id, user_id=user_id)
            if not chat:
                return []

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT message_id, chat_id, role, content, metadata, created_at
                FROM messages
                WHERE chat_id = $1
                ORDER BY created_at ASC
                """,
                chat_id,
            )
            return [self._row_to_message(row) for row in rows]

    @staticmethod
    def _row_to_chat(row) -> dict[str, Any]:
        doc_ids = row["document_ids"]
        if isinstance(doc_ids, str):
            doc_ids = json.loads(doc_ids)
        return {
            "chat_id": row["chat_id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "mode": row["mode"],
            "document_ids": doc_ids or [],
            "created_at": row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else str(row["created_at"]),
            "updated_at": row["updated_at"].isoformat() if isinstance(row["updated_at"], datetime) else str(row["updated_at"]),
        }

    @staticmethod
    def _row_to_message(row) -> dict[str, Any]:
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        content_val = row["content"]
        if not isinstance(content_val, str):
            content_val = json.dumps(content_val) if content_val is not None else ""
        return {
            "message_id": row["message_id"],
            "chat_id": row["chat_id"],
            "role": row["role"],
            "content": content_val,
            "metadata": meta or {},
            "created_at": row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else str(row["created_at"]),
        }


def create_chat_registry() -> ChatRegistryProtocol:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.info("DATABASE_URL not set — using InMemoryChatRegistry fallback.")
        return InMemoryChatRegistry()

    try:
        import asyncpg  # noqa: F401
    except ImportError:
        logger.warning("DATABASE_URL is set but `asyncpg` is not installed; using InMemoryChatRegistry.")
        return InMemoryChatRegistry()

    return PostgresChatRegistry(database_url)
