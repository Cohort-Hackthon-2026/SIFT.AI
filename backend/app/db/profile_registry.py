"""User-profile registry (BE2, plan §3.1 `user_profiles`).

One row per Clerk user holding onboarding data: role, NBA enrolment number,
default jurisdiction, and the chambers they belong to (if any). Backed by
Postgres when ``DATABASE_URL`` is set, otherwise an in-memory dict so the API
boots and the FE onboarding flow works locally.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

logger = logging.getLogger(__name__)

VALID_ROLES = {"PRINCIPAL", "PARTNER", "ASSOCIATE", "TRAINEE", "LAW_STUDENT", "SAN"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProfileRegistryProtocol(Protocol):
    async def initialize(self) -> None: ...

    async def get_profile(self, user_id: str) -> dict[str, Any] | None: ...

    async def upsert_profile(
        self,
        user_id: str,
        role: str | None = None,
        nba_number: str | None = None,
        default_jurisdiction: str | None = None,
        chambers_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def delete_profile(self, user_id: str) -> bool: ...


def _new_profile(user_id: str) -> dict[str, Any]:
    now = utc_now().isoformat()
    return {
        "user_id": user_id,
        "role": "ASSOCIATE",
        "nba_number": None,
        "chambers_id": None,
        "default_jurisdiction": "NG",
        "onboarded_at": now,
        "updated_at": now,
    }


def _apply_updates(
    profile: dict[str, Any],
    role: str | None,
    nba_number: str | None,
    default_jurisdiction: str | None,
    chambers_id: str | None,
    *,
    chambers_explicit: bool,
) -> None:
    if role is not None:
        profile["role"] = role.upper()
    if nba_number is not None:
        profile["nba_number"] = nba_number or None
    if default_jurisdiction is not None:
        profile["default_jurisdiction"] = default_jurisdiction.upper()
    if chambers_explicit:
        profile["chambers_id"] = chambers_id
    profile["updated_at"] = utc_now().isoformat()


@dataclass
class InMemoryProfileRegistry:
    _profiles: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def initialize(self) -> None:
        return

    async def get_profile(self, user_id: str) -> dict[str, Any] | None:
        return self._profiles.get(user_id)

    async def upsert_profile(
        self,
        user_id: str,
        role: str | None = None,
        nba_number: str | None = None,
        default_jurisdiction: str | None = None,
        chambers_id: str | None = None,
        _chambers_explicit: bool | None = None,
    ) -> dict[str, Any]:
        profile = self._profiles.get(user_id) or _new_profile(user_id)
        # `chambers_id=None` is ambiguous (leave-alone vs clear); default to
        # "explicit only when a value is passed" unless the caller overrides.
        chambers_explicit = _chambers_explicit if _chambers_explicit is not None else (chambers_id is not None)
        _apply_updates(
            profile, role, nba_number, default_jurisdiction, chambers_id,
            chambers_explicit=chambers_explicit,
        )
        self._profiles[user_id] = profile
        return profile

    async def delete_profile(self, user_id: str) -> bool:
        return self._profiles.pop(user_id, None) is not None


class PostgresProfileRegistry:
    """SQLAlchemy-backed profile registry sharing the app engine (db.session)."""

    def __init__(self) -> None:
        self._sm = None
        self._fallback = InMemoryProfileRegistry()
        self._degraded = False

    async def initialize(self) -> None:
        from app.db.session import get_sessionmaker, init_models

        await init_models()
        self._sm = get_sessionmaker()
        self._degraded = self._sm is None

    async def get_profile(self, user_id: str) -> dict[str, Any] | None:
        if self._degraded or self._sm is None:
            return await self._fallback.get_profile(user_id)
        try:
            from app.db.models import UserProfile

            async with self._sm() as session:
                row = await session.get(UserProfile, user_id)
                return row.to_dict() if row else None
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ProfileRegistry.get_profile failed: %s", exc)
            return await self._fallback.get_profile(user_id)

    async def upsert_profile(
        self,
        user_id: str,
        role: str | None = None,
        nba_number: str | None = None,
        default_jurisdiction: str | None = None,
        chambers_id: str | None = None,
        _chambers_explicit: bool | None = None,
    ) -> dict[str, Any]:
        if self._degraded or self._sm is None:
            return await self._fallback.upsert_profile(
                user_id, role, nba_number, default_jurisdiction, chambers_id, _chambers_explicit
            )
        chambers_explicit = _chambers_explicit if _chambers_explicit is not None else (chambers_id is not None)
        try:
            from app.db.models import UserProfile

            async with self._sm() as session:
                row = await session.get(UserProfile, user_id)
                now = utc_now()
                if row is None:
                    row = UserProfile(
                        user_id=user_id,
                        role=(role or "ASSOCIATE").upper(),
                        nba_number=nba_number or None,
                        chambers_id=chambers_id if chambers_explicit else None,
                        default_jurisdiction=(default_jurisdiction or "NG").upper(),
                        onboarded_at=now,
                        updated_at=now,
                    )
                    session.add(row)
                else:
                    if role is not None:
                        row.role = role.upper()
                    if nba_number is not None:
                        row.nba_number = nba_number or None
                    if default_jurisdiction is not None:
                        row.default_jurisdiction = default_jurisdiction.upper()
                    if chambers_explicit:
                        row.chambers_id = chambers_id
                    row.updated_at = now
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ProfileRegistry.upsert_profile failed: %s", exc)
            return await self._fallback.upsert_profile(
                user_id, role, nba_number, default_jurisdiction, chambers_id, _chambers_explicit
            )

    async def delete_profile(self, user_id: str) -> bool:
        if self._degraded or self._sm is None:
            return await self._fallback.delete_profile(user_id)
        try:
            from app.db.models import UserProfile

            async with self._sm() as session:
                row = await session.get(UserProfile, user_id)
                if row is None:
                    return False
                await session.delete(row)
                await session.commit()
                return True
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("ProfileRegistry.delete_profile failed: %s", exc)
            return await self._fallback.delete_profile(user_id)


def create_profile_registry() -> ProfileRegistryProtocol:
    from app.db.session import database_configured

    if not database_configured():
        return InMemoryProfileRegistry()
    return PostgresProfileRegistry()
