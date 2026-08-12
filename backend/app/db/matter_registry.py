"""Matter registry (BE2, plan §3.1 `matters`).

A matter is a case workspace. Documents and chats carry a nullable
``matter_id`` that files them under a matter. Visibility is role-based and
composed in the route layer: this registry exposes the low-level "by creator"
and "by chambers" lookups; the route merges them using the caller's chambers
membership role (PRINCIPAL/PARTNER see all chambers matters; others see own).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)

VALID_PRACTICE_AREAS = {
    "LITIGATION", "CORPORATE", "PROPERTY", "ENERGY", "FAMILY", "CRIMINAL",
    "IP", "TAX", "EMPLOYMENT", "OTHER",
}
VALID_MATTER_STATUS = {"OPEN", "CLOSED", "ARCHIVED"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MatterRegistryProtocol(Protocol):
    async def initialize(self) -> None: ...

    async def create_matter(
        self,
        created_by_user_id: str,
        title: str,
        client_name: str | None = None,
        practice_area: str = "OTHER",
        jurisdiction: str = "NG",
        chambers_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def get_matter(self, matter_id: str) -> dict[str, Any] | None: ...

    async def list_by_creator(self, user_id: str) -> list[dict[str, Any]]: ...

    async def list_by_chambers(self, chambers_id: str) -> list[dict[str, Any]]: ...

    async def update_matter(self, matter_id: str, **fields: Any) -> dict[str, Any] | None: ...

    async def delete_matter(self, matter_id: str) -> bool: ...

    async def delete_matters_for_user(self, user_id: str) -> list[str]: ...


_UPDATABLE = {"title", "client_name", "practice_area", "jurisdiction", "status", "chambers_id"}


@dataclass
class InMemoryMatterRegistry:
    _matters: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def initialize(self) -> None:
        return

    async def create_matter(
        self,
        created_by_user_id: str,
        title: str,
        client_name: str | None = None,
        practice_area: str = "OTHER",
        jurisdiction: str = "NG",
        chambers_id: str | None = None,
    ) -> dict[str, Any]:
        matter_id = str(uuid4())
        now = utc_now().isoformat()
        record = {
            "matter_id": matter_id,
            "chambers_id": chambers_id,
            "created_by_user_id": created_by_user_id,
            "title": title,
            "client_name": client_name,
            "practice_area": (practice_area or "OTHER").upper(),
            "jurisdiction": (jurisdiction or "NG").upper(),
            "status": "OPEN",
            "created_at": now,
            "updated_at": now,
        }
        self._matters[matter_id] = record
        return record

    async def get_matter(self, matter_id: str) -> dict[str, Any] | None:
        return self._matters.get(matter_id)

    async def list_by_creator(self, user_id: str) -> list[dict[str, Any]]:
        rows = [m for m in self._matters.values() if m["created_by_user_id"] == user_id]
        return sorted(rows, key=lambda m: m["created_at"], reverse=True)

    async def list_by_chambers(self, chambers_id: str) -> list[dict[str, Any]]:
        rows = [m for m in self._matters.values() if m.get("chambers_id") == chambers_id]
        return sorted(rows, key=lambda m: m["created_at"], reverse=True)

    async def update_matter(self, matter_id: str, **fields: Any) -> dict[str, Any] | None:
        record = self._matters.get(matter_id)
        if not record:
            return None
        for key, value in fields.items():
            if key not in _UPDATABLE or value is None:
                continue
            if key in {"practice_area", "jurisdiction", "status"}:
                value = str(value).upper()
            record[key] = value
        record["updated_at"] = utc_now().isoformat()
        return record

    async def delete_matter(self, matter_id: str) -> bool:
        return self._matters.pop(matter_id, None) is not None

    async def delete_matters_for_user(self, user_id: str) -> list[str]:
        ids = [mid for mid, m in self._matters.items() if m["created_by_user_id"] == user_id]
        for mid in ids:
            self._matters.pop(mid, None)
        return ids


class PostgresMatterRegistry:
    def __init__(self) -> None:
        self._sm = None
        self._fallback = InMemoryMatterRegistry()
        self._degraded = False

    async def initialize(self) -> None:
        from app.db.session import get_sessionmaker, init_models

        await init_models()
        self._sm = get_sessionmaker()
        self._degraded = self._sm is None

    def _down(self) -> bool:
        return self._degraded or self._sm is None

    async def create_matter(
        self,
        created_by_user_id: str,
        title: str,
        client_name: str | None = None,
        practice_area: str = "OTHER",
        jurisdiction: str = "NG",
        chambers_id: str | None = None,
    ) -> dict[str, Any]:
        if self._down():
            return await self._fallback.create_matter(
                created_by_user_id, title, client_name, practice_area, jurisdiction, chambers_id
            )
        try:
            from app.db.models import Matter

            now = utc_now()
            async with self._sm() as session:
                row = Matter(
                    matter_id=str(uuid4()),
                    chambers_id=chambers_id,
                    created_by_user_id=created_by_user_id,
                    title=title,
                    client_name=client_name,
                    practice_area=(practice_area or "OTHER").upper(),
                    jurisdiction=(jurisdiction or "NG").upper(),
                    status="OPEN",
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("MatterRegistry.create_matter failed: %s", exc)
            return await self._fallback.create_matter(
                created_by_user_id, title, client_name, practice_area, jurisdiction, chambers_id
            )

    async def get_matter(self, matter_id: str) -> dict[str, Any] | None:
        if self._down():
            return await self._fallback.get_matter(matter_id)
        try:
            from app.db.models import Matter

            async with self._sm() as session:
                row = await session.get(Matter, matter_id)
                return row.to_dict() if row else None
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("MatterRegistry.get_matter failed: %s", exc)
            return await self._fallback.get_matter(matter_id)

    async def list_by_creator(self, user_id: str) -> list[dict[str, Any]]:
        if self._down():
            return await self._fallback.list_by_creator(user_id)
        try:
            from sqlalchemy import select

            from app.db.models import Matter

            async with self._sm() as session:
                stmt = (
                    select(Matter)
                    .where(Matter.created_by_user_id == user_id)
                    .order_by(Matter.created_at.desc())
                )
                rows = (await session.execute(stmt)).scalars().all()
                return [r.to_dict() for r in rows]
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("MatterRegistry.list_by_creator failed: %s", exc)
            return await self._fallback.list_by_creator(user_id)

    async def list_by_chambers(self, chambers_id: str) -> list[dict[str, Any]]:
        if self._down():
            return await self._fallback.list_by_chambers(chambers_id)
        try:
            from sqlalchemy import select

            from app.db.models import Matter

            async with self._sm() as session:
                stmt = (
                    select(Matter)
                    .where(Matter.chambers_id == chambers_id)
                    .order_by(Matter.created_at.desc())
                )
                rows = (await session.execute(stmt)).scalars().all()
                return [r.to_dict() for r in rows]
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("MatterRegistry.list_by_chambers failed: %s", exc)
            return await self._fallback.list_by_chambers(chambers_id)

    async def update_matter(self, matter_id: str, **fields: Any) -> dict[str, Any] | None:
        if self._down():
            return await self._fallback.update_matter(matter_id, **fields)
        try:
            from app.db.models import Matter

            async with self._sm() as session:
                row = await session.get(Matter, matter_id)
                if row is None:
                    return None
                for key, value in fields.items():
                    if key not in _UPDATABLE or value is None:
                        continue
                    if key in {"practice_area", "jurisdiction", "status"}:
                        value = str(value).upper()
                    setattr(row, key, value)
                row.updated_at = utc_now()
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("MatterRegistry.update_matter failed: %s", exc)
            return await self._fallback.update_matter(matter_id, **fields)

    async def delete_matter(self, matter_id: str) -> bool:
        if self._down():
            return await self._fallback.delete_matter(matter_id)
        try:
            from app.db.models import Matter

            async with self._sm() as session:
                row = await session.get(Matter, matter_id)
                if row is None:
                    return False
                await session.delete(row)
                await session.commit()
                return True
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("MatterRegistry.delete_matter failed: %s", exc)
            return await self._fallback.delete_matter(matter_id)

    async def delete_matters_for_user(self, user_id: str) -> list[str]:
        if self._down():
            return await self._fallback.delete_matters_for_user(user_id)
        try:
            from sqlalchemy import select

            from app.db.models import Matter

            async with self._sm() as session:
                stmt = select(Matter).where(Matter.created_by_user_id == user_id)
                rows = (await session.execute(stmt)).scalars().all()
                ids = [r.matter_id for r in rows]
                for r in rows:
                    await session.delete(r)
                await session.commit()
                return ids
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("MatterRegistry.delete_matters_for_user failed: %s", exc)
            return await self._fallback.delete_matters_for_user(user_id)


def create_matter_registry() -> MatterRegistryProtocol:
    from app.db.session import database_configured

    if not database_configured():
        return InMemoryMatterRegistry()
    return PostgresMatterRegistry()
