"""Billing registry (BE2, plan §3.1 `subscriptions` + `usage_events`).

Two concerns behind one registry:

* **usage_events** — an append-only meter. Every billable action
  (QUERY / DOC_UPLOAD / EXPORT / AUDIO_MIN) records a row; ``usage_summary``
  aggregates them for the billing dashboard and tier enforcement.
* **subscriptions** — billing history rows (period + Paystack ``external_ref``).
  The *current* tier of a chambers lives on ``chambers.subscription_tier`` (the
  source of truth for gating); this table records how it got there.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)

VALID_EVENT_TYPES = {"QUERY", "DOC_UPLOAD", "EXPORT", "AUDIO_MIN"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts: Any) -> datetime | None:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None
    return None


class BillingRegistryProtocol(Protocol):
    async def initialize(self) -> None: ...

    async def record_usage(
        self,
        user_id: str,
        event_type: str,
        quantity: int = 1,
        chambers_id: str | None = None,
    ) -> dict[str, Any]: ...

    async def usage_summary(
        self,
        chambers_id: str | None = None,
        user_id: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, int]: ...

    async def create_subscription(
        self,
        chambers_id: str,
        tier: str,
        status: str = "ACTIVE",
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        external_ref: str | None = None,
    ) -> dict[str, Any]: ...

    async def get_active_subscription(self, chambers_id: str) -> dict[str, Any] | None: ...

    async def list_subscriptions(self, chambers_id: str) -> list[dict[str, Any]]: ...

    async def delete_usage_for_user(self, user_id: str) -> int: ...


@dataclass
class InMemoryBillingRegistry:
    _usage: list[dict[str, Any]] = field(default_factory=list)
    _subscriptions: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def initialize(self) -> None:
        return

    async def record_usage(
        self,
        user_id: str,
        event_type: str,
        quantity: int = 1,
        chambers_id: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "id": str(uuid4()),
            "chambers_id": chambers_id,
            "user_id": user_id,
            "event_type": event_type.upper(),
            "quantity": int(quantity),
            "created_at": utc_now().isoformat(),
        }
        self._usage.append(record)
        return record

    async def usage_summary(
        self,
        chambers_id: str | None = None,
        user_id: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, int]:
        summary: dict[str, int] = {}
        for row in self._usage:
            if chambers_id is not None and row.get("chambers_id") != chambers_id:
                continue
            if user_id is not None and row.get("user_id") != user_id:
                continue
            if since is not None:
                created = _parse(row.get("created_at"))
                if created is not None and created < since:
                    continue
            summary[row["event_type"]] = summary.get(row["event_type"], 0) + row["quantity"]
        return summary

    async def create_subscription(
        self,
        chambers_id: str,
        tier: str,
        status: str = "ACTIVE",
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        external_ref: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "id": str(uuid4()),
            "chambers_id": chambers_id,
            "tier": tier.upper(),
            "status": status.upper(),
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None,
            "external_ref": external_ref,
            "created_at": utc_now().isoformat(),
        }
        self._subscriptions[record["id"]] = record
        return record

    async def get_active_subscription(self, chambers_id: str) -> dict[str, Any] | None:
        rows = [
            s for s in self._subscriptions.values()
            if s["chambers_id"] == chambers_id and s["status"] == "ACTIVE"
        ]
        if not rows:
            return None
        return sorted(rows, key=lambda s: s["created_at"], reverse=True)[0]

    async def list_subscriptions(self, chambers_id: str) -> list[dict[str, Any]]:
        rows = [s for s in self._subscriptions.values() if s["chambers_id"] == chambers_id]
        return sorted(rows, key=lambda s: s["created_at"], reverse=True)

    async def delete_usage_for_user(self, user_id: str) -> int:
        before = len(self._usage)
        self._usage = [r for r in self._usage if r["user_id"] != user_id]
        return before - len(self._usage)


class PostgresBillingRegistry:
    def __init__(self) -> None:
        self._sm = None
        self._fallback = InMemoryBillingRegistry()
        self._degraded = False

    async def initialize(self) -> None:
        from app.db.session import get_sessionmaker, init_models

        await init_models()
        self._sm = get_sessionmaker()
        self._degraded = self._sm is None

    def _down(self) -> bool:
        return self._degraded or self._sm is None

    async def record_usage(
        self,
        user_id: str,
        event_type: str,
        quantity: int = 1,
        chambers_id: str | None = None,
    ) -> dict[str, Any]:
        if self._down():
            return await self._fallback.record_usage(user_id, event_type, quantity, chambers_id)
        try:
            from app.db.models import UsageEvent

            async with self._sm() as session:
                row = UsageEvent(
                    id=str(uuid4()),
                    chambers_id=chambers_id,
                    user_id=user_id,
                    event_type=event_type.upper(),
                    quantity=int(quantity),
                    created_at=utc_now(),
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("BillingRegistry.record_usage failed: %s", exc)
            return await self._fallback.record_usage(user_id, event_type, quantity, chambers_id)

    async def usage_summary(
        self,
        chambers_id: str | None = None,
        user_id: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, int]:
        if self._down():
            return await self._fallback.usage_summary(chambers_id, user_id, since)
        try:
            from sqlalchemy import func, select

            from app.db.models import UsageEvent

            async with self._sm() as session:
                stmt = select(UsageEvent.event_type, func.sum(UsageEvent.quantity))
                if chambers_id is not None:
                    stmt = stmt.where(UsageEvent.chambers_id == chambers_id)
                if user_id is not None:
                    stmt = stmt.where(UsageEvent.user_id == user_id)
                if since is not None:
                    stmt = stmt.where(UsageEvent.created_at >= since)
                stmt = stmt.group_by(UsageEvent.event_type)
                rows = (await session.execute(stmt)).all()
                return {event_type: int(total or 0) for event_type, total in rows}
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("BillingRegistry.usage_summary failed: %s", exc)
            return await self._fallback.usage_summary(chambers_id, user_id, since)

    async def create_subscription(
        self,
        chambers_id: str,
        tier: str,
        status: str = "ACTIVE",
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        external_ref: str | None = None,
    ) -> dict[str, Any]:
        if self._down():
            return await self._fallback.create_subscription(
                chambers_id, tier, status, period_start, period_end, external_ref
            )
        try:
            from app.db.models import Subscription

            async with self._sm() as session:
                row = Subscription(
                    id=str(uuid4()),
                    chambers_id=chambers_id,
                    tier=tier.upper(),
                    status=status.upper(),
                    period_start=period_start,
                    period_end=period_end,
                    external_ref=external_ref,
                    created_at=utc_now(),
                )
                session.add(row)
                await session.commit()
                await session.refresh(row)
                return row.to_dict()
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("BillingRegistry.create_subscription failed: %s", exc)
            return await self._fallback.create_subscription(
                chambers_id, tier, status, period_start, period_end, external_ref
            )

    async def get_active_subscription(self, chambers_id: str) -> dict[str, Any] | None:
        if self._down():
            return await self._fallback.get_active_subscription(chambers_id)
        try:
            from sqlalchemy import select

            from app.db.models import Subscription

            async with self._sm() as session:
                stmt = (
                    select(Subscription)
                    .where(Subscription.chambers_id == chambers_id, Subscription.status == "ACTIVE")
                    .order_by(Subscription.created_at.desc())
                )
                row = (await session.execute(stmt)).scalars().first()
                return row.to_dict() if row else None
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("BillingRegistry.get_active_subscription failed: %s", exc)
            return await self._fallback.get_active_subscription(chambers_id)

    async def list_subscriptions(self, chambers_id: str) -> list[dict[str, Any]]:
        if self._down():
            return await self._fallback.list_subscriptions(chambers_id)
        try:
            from sqlalchemy import select

            from app.db.models import Subscription

            async with self._sm() as session:
                stmt = (
                    select(Subscription)
                    .where(Subscription.chambers_id == chambers_id)
                    .order_by(Subscription.created_at.desc())
                )
                rows = (await session.execute(stmt)).scalars().all()
                return [r.to_dict() for r in rows]
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("BillingRegistry.list_subscriptions failed: %s", exc)
            return await self._fallback.list_subscriptions(chambers_id)

    async def delete_usage_for_user(self, user_id: str) -> int:
        if self._down():
            return await self._fallback.delete_usage_for_user(user_id)
        try:
            from sqlalchemy import delete

            from app.db.models import UsageEvent

            async with self._sm() as session:
                result = await session.execute(
                    delete(UsageEvent).where(UsageEvent.user_id == user_id)
                )
                await session.commit()
                return result.rowcount or 0
        except Exception as exc:  # pragma: no cover - needs live DB
            logger.error("BillingRegistry.delete_usage_for_user failed: %s", exc)
            return await self._fallback.delete_usage_for_user(user_id)


def create_billing_registry() -> BillingRegistryProtocol:
    from app.db.session import database_configured

    if not database_configured():
        return InMemoryBillingRegistry()
    return PostgresBillingRegistry()
