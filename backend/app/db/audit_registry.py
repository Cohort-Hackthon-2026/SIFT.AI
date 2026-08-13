"""Audit-log registry (BE2, plan §3.1 `audit_log`).

Append-only compliance trail: who did what, when, against which matter. Written
by any route that touches user data (profile edits, matter changes, exports,
erasure) and read back by the Enterprise audit endpoint. ``detail`` is free-form
JSON for action-specific context.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditRegistryProtocol(Protocol):
    async def initialize(self) -> None: ...

    async def record(
        self,
        user_id: str,
        action: str,
        chambers_id: str | None = None,
        matter_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def list_logs(
        self,
        chambers_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    async def delete_logs_for_user(self, user_id: str) -> int: ...


@dataclass
class InMemoryAuditRegistry:
    _logs: list[dict[str, Any]] = field(default_factory=list)

    async def initialize(self) -> None:
        return

    async def record(
        self,
        user_id: str,
        action: str,
        chambers_id: str | None = None,
        matter_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "id": str(uuid4()),
            "chambers_id": chambers_id,
            "user_id": user_id,
            "action": action.upper(),
            "matter_id": matter_id,
            "detail": detail or {},
            "created_at": utc_now().isoformat(),
        }
        self._logs.append(record)
        return record

    async def list_logs(
        self,
        chambers_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        rows = self._logs
        if chambers_id is not None:
            rows = [r for r in rows if r.get("chambers_id") == chambers_id]
        if user_id is not None:
            rows = [r for r in rows if r.get("user_id") == user_id]
        rows = sorted(rows, key=lambda r: r["created_at"], reverse=True)
        return rows[: max(0, limit)]

    async def delete_logs_for_user(self, user_id: str) -> int:
        before = len(self._logs)
        self._logs = [r for r in self._logs if r["user_id"] != user_id]
        return before - len(self._logs)


class PostgresAuditRegistry:
    def __init__(self) -> None:
        self._sm = None
        self._fallback = InMemoryAuditRegistry()
        self._degraded = False

    async def initialize(self) -> None:
        from app.db.session import get_sessionmaker, init_models

        await init_models()
        self._sm = get_sessionmaker()
        self._degraded = self._sm is None

    def _down(self) -> bool:
        return self._degraded or self._sm is None

    async def record(
        self,
        user_id: str,
        action: str,
        chambers_id: str | None = None,
        matter_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._down():
            return await self._fallback.record(user_id, action, chambers_id, matter_id, detail)
        try:
            from app.db.models import AuditLog

            async with self._sm() as session:
                row = AuditLog(
                    id=str(uuid4()),
                    chambers_id=chambers_id,
                    user_id=user_id,
                    action=action.upper(),
                    matter_id=matter_id,
                    detail=detail or {},
                    created_at=utc_now(),
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("AuditRegistry.record failed: %s", exc)
            return await self._fallback.record(user_id, action, chambers_id, matter_id, detail)

    async def list_logs(
        self,
        chambers_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if self._down():
            return await self._fallback.list_logs(chambers_id, user_id, limit)
        try:
            from sqlalchemy import select

            from app.db.models import AuditLog

            async with self._sm() as session:
                stmt = select(AuditLog)
                if chambers_id is not None:
                    stmt = stmt.where(AuditLog.chambers_id == chambers_id)
                if user_id is not None:
                    stmt = stmt.where(AuditLog.user_id == user_id)
                stmt = stmt.order_by(AuditLog.created_at.desc()).limit(max(0, limit))
                rows = (await session.execute(stmt)).scalars().all()
                return [r.to_dict() for r in rows]
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("AuditRegistry.list_logs failed: %s", exc)
            return await self._fallback.list_logs(chambers_id, user_id, limit)

    async def delete_logs_for_user(self, user_id: str) -> int:
        if self._down():
            return await self._fallback.delete_logs_for_user(user_id)
        try:
            from sqlalchemy import delete

            from app.db.models import AuditLog

            async with self._sm() as session:
                result = await session.execute(
                    delete(AuditLog).where(AuditLog.user_id == user_id)
                )
                await session.commit()
                return result.rowcount or 0
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("AuditRegistry.delete_logs_for_user failed: %s", exc)
            return await self._fallback.delete_logs_for_user(user_id)


def create_audit_registry() -> AuditRegistryProtocol:
    from app.db.session import database_configured

    if not database_configured():
        return InMemoryAuditRegistry()
    return PostgresAuditRegistry()
