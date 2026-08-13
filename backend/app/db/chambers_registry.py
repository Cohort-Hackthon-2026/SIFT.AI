"""Chambers registry (BE2, plan §3.1 `chambers` + `chambers_memberships`).

A chambers is the team-account root: it owns matters, carries the subscription
tier, and has members with roles (PRINCIPAL/PARTNER/ASSOCIATE/TRAINEE). New
members join via a short invite code minted at creation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)

VALID_MEMBER_ROLES = {"PRINCIPAL", "PARTNER", "ASSOCIATE", "TRAINEE"}
VALID_TIERS = {"FREE", "STARTER", "PRO", "ENTERPRISE"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_invite_code() -> str:
    return uuid4().hex[:8].upper()


class ChambersRegistryProtocol(Protocol):
    async def initialize(self) -> None: ...

    async def create_chambers(self, name: str, created_by_user_id: str) -> dict[str, Any]: ...

    async def get_chambers(self, chambers_id: str) -> dict[str, Any] | None: ...

    async def get_chambers_by_invite(self, invite_code: str) -> dict[str, Any] | None: ...

    async def list_chambers_for_user(self, user_id: str) -> list[dict[str, Any]]: ...

    async def get_membership(self, chambers_id: str, user_id: str) -> dict[str, Any] | None: ...

    async def list_members(self, chambers_id: str) -> list[dict[str, Any]]: ...

    async def add_member(
        self, chambers_id: str, user_id: str, role: str = "ASSOCIATE", status: str = "ACTIVE"
    ) -> dict[str, Any]: ...

    async def set_tier(self, chambers_id: str, tier: str) -> dict[str, Any] | None: ...

    async def set_residency(
        self, chambers_id: str, data_region: str | None = None, retention_days: int | None = None
    ) -> dict[str, Any] | None: ...

    async def remove_member(self, chambers_id: str, user_id: str) -> bool: ...

    async def remove_memberships_for_user(self, user_id: str) -> int: ...


@dataclass
class InMemoryChambersRegistry:
    _chambers: dict[str, dict[str, Any]] = field(default_factory=dict)
    _memberships: dict[str, dict[str, Any]] = field(default_factory=dict)  # membership_id -> row

    async def initialize(self) -> None:
        return

    async def create_chambers(self, name: str, created_by_user_id: str) -> dict[str, Any]:
        chambers_id = str(uuid4())
        now = utc_now().isoformat()
        record = {
            "chambers_id": chambers_id,
            "name": name,
            "subscription_tier": "FREE",
            "invite_code": _new_invite_code(),
            "created_by_user_id": created_by_user_id,
            "data_region": None,
            "retention_days": None,
            "created_at": now,
        }
        self._chambers[chambers_id] = record
        # Creator is the founding PRINCIPAL.
        await self.add_member(chambers_id, created_by_user_id, role="PRINCIPAL")
        return record

    async def get_chambers(self, chambers_id: str) -> dict[str, Any] | None:
        return self._chambers.get(chambers_id)

    async def get_chambers_by_invite(self, invite_code: str) -> dict[str, Any] | None:
        for record in self._chambers.values():
            if record.get("invite_code") == invite_code:
                return record
        return None

    async def list_chambers_for_user(self, user_id: str) -> list[dict[str, Any]]:
        ids = {m["chambers_id"] for m in self._memberships.values() if m["user_id"] == user_id}
        return [self._chambers[cid] for cid in ids if cid in self._chambers]

    async def get_membership(self, chambers_id: str, user_id: str) -> dict[str, Any] | None:
        for m in self._memberships.values():
            if m["chambers_id"] == chambers_id and m["user_id"] == user_id:
                return m
        return None

    async def list_members(self, chambers_id: str) -> list[dict[str, Any]]:
        return [m for m in self._memberships.values() if m["chambers_id"] == chambers_id]

    async def add_member(
        self, chambers_id: str, user_id: str, role: str = "ASSOCIATE", status: str = "ACTIVE"
    ) -> dict[str, Any]:
        existing = await self.get_membership(chambers_id, user_id)
        if existing:
            existing["role"] = role.upper()
            existing["status"] = status.upper()
            return existing
        membership_id = str(uuid4())
        record = {
            "id": membership_id,
            "chambers_id": chambers_id,
            "user_id": user_id,
            "role": role.upper(),
            "status": status.upper(),
            "created_at": utc_now().isoformat(),
        }
        self._memberships[membership_id] = record
        return record

    async def set_tier(self, chambers_id: str, tier: str) -> dict[str, Any] | None:
        record = self._chambers.get(chambers_id)
        if not record:
            return None
        record["subscription_tier"] = tier.upper()
        return record

    async def set_residency(
        self, chambers_id: str, data_region: str | None = None, retention_days: int | None = None
    ) -> dict[str, Any] | None:
        record = self._chambers.get(chambers_id)
        if not record:
            return None
        if data_region is not None:
            record["data_region"] = data_region
        if retention_days is not None:
            record["retention_days"] = retention_days
        return record

    async def remove_memberships_for_user(self, user_id: str) -> int:
        to_remove = [mid for mid, m in self._memberships.items() if m["user_id"] == user_id]
        for mid in to_remove:
            self._memberships.pop(mid, None)
        return len(to_remove)

    async def remove_member(self, chambers_id: str, user_id: str) -> bool:
        to_remove = [
            mid for mid, m in self._memberships.items()
            if m["chambers_id"] == chambers_id and m["user_id"] == user_id
        ]
        for mid in to_remove:
            self._memberships.pop(mid, None)
        return bool(to_remove)


class PostgresChambersRegistry:
    def __init__(self) -> None:
        self._sm = None
        self._fallback = InMemoryChambersRegistry()
        self._degraded = False

    async def initialize(self) -> None:
        from app.db.session import get_sessionmaker, init_models

        await init_models()
        self._sm = get_sessionmaker()
        self._degraded = self._sm is None

    def _down(self) -> bool:
        return self._degraded or self._sm is None

    async def create_chambers(self, name: str, created_by_user_id: str) -> dict[str, Any]:
        if self._down():
            return await self._fallback.create_chambers(name, created_by_user_id)
        try:
            from app.db.models import Chambers

            chambers_id = str(uuid4())
            now = utc_now()
            async with self._sm() as session:
                row = Chambers(
                    chambers_id=chambers_id,
                    name=name,
                    subscription_tier="FREE",
                    invite_code=_new_invite_code(),
                    created_by_user_id=created_by_user_id,
                    created_at=now,
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                result = row.to_dict()
            await self.add_member(chambers_id, created_by_user_id, role="PRINCIPAL")
            return result
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.create_chambers failed: %s", exc)
            return await self._fallback.create_chambers(name, created_by_user_id)

    async def get_chambers(self, chambers_id: str) -> dict[str, Any] | None:
        if self._down():
            return await self._fallback.get_chambers(chambers_id)
        try:
            from app.db.models import Chambers

            async with self._sm() as session:
                row = await session.get(Chambers, chambers_id)
                return row.to_dict() if row else None
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.get_chambers failed: %s", exc)
            return await self._fallback.get_chambers(chambers_id)

    async def get_chambers_by_invite(self, invite_code: str) -> dict[str, Any] | None:
        if self._down():
            return await self._fallback.get_chambers_by_invite(invite_code)
        try:
            from sqlalchemy import select

            from app.db.models import Chambers

            async with self._sm() as session:
                stmt = select(Chambers).where(Chambers.invite_code == invite_code)
                row = (await session.execute(stmt)).scalars().first()
                return row.to_dict() if row else None
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.get_chambers_by_invite failed: %s", exc)
            return await self._fallback.get_chambers_by_invite(invite_code)

    async def list_chambers_for_user(self, user_id: str) -> list[dict[str, Any]]:
        if self._down():
            return await self._fallback.list_chambers_for_user(user_id)
        try:
            from sqlalchemy import select

            from app.db.models import Chambers, ChambersMembership

            async with self._sm() as session:
                stmt = (
                    select(Chambers)
                    .join(ChambersMembership, ChambersMembership.chambers_id == Chambers.chambers_id)
                    .where(ChambersMembership.user_id == user_id)
                )
                rows = (await session.execute(stmt)).scalars().all()
                return [r.to_dict() for r in rows]
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.list_chambers_for_user failed: %s", exc)
            return await self._fallback.list_chambers_for_user(user_id)

    async def get_membership(self, chambers_id: str, user_id: str) -> dict[str, Any] | None:
        if self._down():
            return await self._fallback.get_membership(chambers_id, user_id)
        try:
            from sqlalchemy import select

            from app.db.models import ChambersMembership

            async with self._sm() as session:
                stmt = select(ChambersMembership).where(
                    ChambersMembership.chambers_id == chambers_id,
                    ChambersMembership.user_id == user_id,
                )
                row = (await session.execute(stmt)).scalars().first()
                return row.to_dict() if row else None
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.get_membership failed: %s", exc)
            return await self._fallback.get_membership(chambers_id, user_id)

    async def list_members(self, chambers_id: str) -> list[dict[str, Any]]:
        if self._down():
            return await self._fallback.list_members(chambers_id)
        try:
            from sqlalchemy import select

            from app.db.models import ChambersMembership

            async with self._sm() as session:
                stmt = select(ChambersMembership).where(ChambersMembership.chambers_id == chambers_id)
                rows = (await session.execute(stmt)).scalars().all()
                return [r.to_dict() for r in rows]
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.list_members failed: %s", exc)
            return await self._fallback.list_members(chambers_id)

    async def add_member(
        self, chambers_id: str, user_id: str, role: str = "ASSOCIATE", status: str = "ACTIVE"
    ) -> dict[str, Any]:
        if self._down():
            return await self._fallback.add_member(chambers_id, user_id, role, status)
        try:
            from sqlalchemy import select

            from app.db.models import ChambersMembership

            async with self._sm() as session:
                stmt = select(ChambersMembership).where(
                    ChambersMembership.chambers_id == chambers_id,
                    ChambersMembership.user_id == user_id,
                )
                row = (await session.execute(stmt)).scalars().first()
                if row is None:
                    row = ChambersMembership(
                        id=str(uuid4()),
                        chambers_id=chambers_id,
                        user_id=user_id,
                        role=role.upper(),
                        status=status.upper(),
                        created_at=utc_now(),
                    )
                    session.add(row)
                else:
                    row.role = role.upper()
                    row.status = status.upper()
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.add_member failed: %s", exc)
            return await self._fallback.add_member(chambers_id, user_id, role, status)

    async def set_tier(self, chambers_id: str, tier: str) -> dict[str, Any] | None:
        if self._down():
            return await self._fallback.set_tier(chambers_id, tier)
        try:
            from app.db.models import Chambers

            async with self._sm() as session:
                row = await session.get(Chambers, chambers_id)
                if row is None:
                    return None
                row.subscription_tier = tier.upper()
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.set_tier failed: %s", exc)
            return await self._fallback.set_tier(chambers_id, tier)

    async def set_residency(
        self, chambers_id: str, data_region: str | None = None, retention_days: int | None = None
    ) -> dict[str, Any] | None:
        if self._down():
            return await self._fallback.set_residency(chambers_id, data_region, retention_days)
        try:
            from app.db.models import Chambers

            async with self._sm() as session:
                row = await session.get(Chambers, chambers_id)
                if row is None:
                    return None
                if data_region is not None:
                    row.data_region = data_region
                if retention_days is not None:
                    row.retention_days = retention_days
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.set_residency failed: %s", exc)
            return await self._fallback.set_residency(chambers_id, data_region, retention_days)

    async def remove_memberships_for_user(self, user_id: str) -> int:
        if self._down():
            return await self._fallback.remove_memberships_for_user(user_id)
        try:
            from sqlalchemy import delete

            from app.db.models import ChambersMembership

            async with self._sm() as session:
                result = await session.execute(
                    delete(ChambersMembership).where(ChambersMembership.user_id == user_id)
                )
                await session.commit()
                return result.rowcount or 0
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.remove_memberships_for_user failed: %s", exc)
            return await self._fallback.remove_memberships_for_user(user_id)

    async def remove_member(self, chambers_id: str, user_id: str) -> bool:
        if self._down():
            return await self._fallback.remove_member(chambers_id, user_id)
        try:
            from sqlalchemy import delete

            from app.db.models import ChambersMembership

            async with self._sm() as session:
                result = await session.execute(
                    delete(ChambersMembership).where(
                        ChambersMembership.chambers_id == chambers_id,
                        ChambersMembership.user_id == user_id,
                    )
                )
                await session.commit()
                return (result.rowcount or 0) > 0
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ChambersRegistry.remove_member failed: %s", exc)
            return await self._fallback.remove_member(chambers_id, user_id)


def create_chambers_registry() -> ChambersRegistryProtocol:
    from app.db.session import database_configured

    if not database_configured():
        return InMemoryChambersRegistry()
    return PostgresChambersRegistry()
