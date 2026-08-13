from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class DocumentRegistryProtocol(Protocol):
    """Tracks document-level metadata (name, owner, page count, size, upload time).

    Ahnlich only knows about individual chunks/vectors + their metadata - it
    has no concept of "a document" as a single listable/deletable entity.
    That's what this registry is for: it backs GET /documents and
    DELETE /documents/{doc_id}, and is the source of truth for document
    listing, while Ahnlich remains the source of truth for chunk search.
    """

    async def initialize(self) -> None: ...

    async def create_document(self, record: dict[str, Any]) -> None: ...

    async def list_documents(self, user_id: str | None = None) -> list[dict[str, Any]]: ...

    async def get_document(self, document_id: str) -> dict[str, Any] | None: ...

    async def delete_document(self, document_id: str) -> bool: ...

    async def set_document_matter(
        self, document_id: str, user_id: str, matter_id: str | None
    ) -> dict[str, Any] | None: ...

    async def list_documents_by_matter(
        self, matter_id: str, user_id: str | None = None
    ) -> list[dict[str, Any]]: ...


@dataclass
class InMemoryDocumentRegistry:
    """Fallback registry used when DATABASE_URL is not configured/reachable."""

    _documents: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def initialize(self) -> None:
        return

    async def create_document(self, record: dict[str, Any]) -> None:
        self._documents[record["document_id"]] = record

    async def list_documents(self, user_id: str | None = None) -> list[dict[str, Any]]:
        documents = list(self._documents.values())
        if user_id:
            documents = [doc for doc in documents if doc.get("user_id") == user_id]
        return sorted(documents, key=lambda doc: doc["uploaded_at"], reverse=True)

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        return self._documents.get(document_id)

    async def delete_document(self, document_id: str) -> bool:
        return self._documents.pop(document_id, None) is not None

    async def set_document_matter(
        self, document_id: str, user_id: str, matter_id: str | None
    ) -> dict[str, Any] | None:
        doc = self._documents.get(document_id)
        if doc is None or doc.get("user_id") != user_id:
            return None
        doc["matter_id"] = matter_id
        return doc

    async def list_documents_by_matter(
        self, matter_id: str, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        docs = [d for d in self._documents.values() if d.get("matter_id") == matter_id]
        if user_id:
            docs = [d for d in docs if d.get("user_id") == user_id]
        return sorted(docs, key=lambda d: d["uploaded_at"], reverse=True)


class PostgresDocumentRegistry:
    """Postgres-backed registry (works with any standard Postgres, e.g. Neon)."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine = None
        self._sessionmaker = None
        self._fallback = InMemoryDocumentRegistry()
        self._last_error: str | None = None

    def _set_last_error(self, error: Exception | None) -> None:
        if error is None:
            self._last_error = None
            return
        self._last_error = f"{type(error).__name__}: {error}"
        logger.error(f"DocumentRegistry Error: {self._last_error}")

    async def initialize(self) -> None:
        try:
            from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

            from app.db.models import Base
        except ImportError as exc:
            self._set_last_error(exc)
            await self._fallback.initialize()
            return

        try:
            if self._engine is None:
                self._engine = create_async_engine(self._database_url, pool_pre_ping=True)
                self._sessionmaker = async_sessionmaker(self._engine, expire_on_commit=False)

            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._last_error = None
        except Exception as exc:  # pragma: no cover - depends on live DB availability
            self._set_last_error(exc)
            await self._fallback.initialize()

    async def create_document(self, record: dict[str, Any]) -> None:
        if self._sessionmaker is None or self._last_error:
            await self._fallback.create_document(record)
            return

        try:
            from app.db.models import DocumentRecord

            # The upload route includes a derived ``file_url`` in the record for
            # the API response; it isn't a column. Filter to real columns so
            # ``DocumentRecord(**record)`` doesn't TypeError on the live DB path
            # (the in-memory fallback just stores the dict verbatim).
            valid_columns = {c.name for c in DocumentRecord.__table__.columns}
            clean = {k: v for k, v in record.items() if k in valid_columns}

            async with self._sessionmaker() as session:
                session.add(DocumentRecord(**clean))
                await session.commit()
        except Exception as exc:  # pragma: no cover - depends on live DB availability
            self._set_last_error(exc)
            await self._fallback.create_document(record)

    async def list_documents(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if self._sessionmaker is None or self._last_error:
            return await self._fallback.list_documents(user_id)

        try:
            from sqlalchemy import select

            from app.db.models import DocumentRecord

            async with self._sessionmaker() as session:
                statement = select(DocumentRecord).order_by(DocumentRecord.uploaded_at.desc())
                if user_id:
                    statement = statement.where(DocumentRecord.user_id == user_id)
                result = await session.execute(statement)
                return [row.to_dict() for row in result.scalars().all()]
        except Exception as exc:  # pragma: no cover - depends on live DB availability
            self._set_last_error(exc)
            return await self._fallback.list_documents(user_id)

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        if self._sessionmaker is None or self._last_error:
            return await self._fallback.get_document(document_id)

        try:
            from app.db.models import DocumentRecord

            async with self._sessionmaker() as session:
                record = await session.get(DocumentRecord, document_id)
                return record.to_dict() if record else None
        except Exception as exc:  # pragma: no cover - depends on live DB availability
            self._set_last_error(exc)
            return await self._fallback.get_document(document_id)

    async def delete_document(self, document_id: str) -> bool:
        if self._sessionmaker is None or self._last_error:
            return await self._fallback.delete_document(document_id)

        try:
            from app.db.models import DocumentRecord

            async with self._sessionmaker() as session:
                record = await session.get(DocumentRecord, document_id)
                if record is None:
                    return False
                await session.delete(record)
                await session.commit()
                return True
        except Exception as exc:  # pragma: no cover - depends on live DB availability
            self._set_last_error(exc)
            return await self._fallback.delete_document(document_id)

    async def set_document_matter(
        self, document_id: str, user_id: str, matter_id: str | None
    ) -> dict[str, Any] | None:
        if self._sessionmaker is None or self._last_error:
            return await self._fallback.set_document_matter(document_id, user_id, matter_id)
        try:
            from app.db.models import DocumentRecord

            async with self._sessionmaker() as session:
                record = await session.get(DocumentRecord, document_id)
                if record is None or record.user_id != user_id:
                    return None
                record.matter_id = matter_id
                await session.commit()
                await session.refresh(record)
                return record.to_dict()
        except Exception as exc:  # pragma: no cover - depends on live DB availability
            self._set_last_error(exc)
            return await self._fallback.set_document_matter(document_id, user_id, matter_id)

    async def list_documents_by_matter(
        self, matter_id: str, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        if self._sessionmaker is None or self._last_error:
            return await self._fallback.list_documents_by_matter(matter_id, user_id)
        try:
            from sqlalchemy import select

            from app.db.models import DocumentRecord

            async with self._sessionmaker() as session:
                statement = (
                    select(DocumentRecord)
                    .where(DocumentRecord.matter_id == matter_id)
                    .order_by(DocumentRecord.uploaded_at.desc())
                )
                if user_id:
                    statement = statement.where(DocumentRecord.user_id == user_id)
                result = await session.execute(statement)
                return [row.to_dict() for row in result.scalars().all()]
        except Exception as exc:  # pragma: no cover - depends on live DB availability
            self._set_last_error(exc)
            return await self._fallback.list_documents_by_matter(matter_id, user_id)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_document_registry() -> DocumentRegistryProtocol:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return InMemoryDocumentRegistry()

    # SQLAlchemy's async engine needs the `+psycopg` (or `+asyncpg`) dialect
    # marker. Neon connection strings are plain `postgresql://...`, which
    # SQLAlchemy would otherwise try to open with the sync psycopg2 driver.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return PostgresDocumentRegistry(database_url)
