from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _iso(value: datetime | None) -> str | None:
    """Serialize a datetime to ISO-8601, mirroring the chat_registry shape so
    in-memory and Postgres registries return byte-identical JSON to the FE."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class DocumentRecord(Base):
    """One row per uploaded document. Chunk-level data lives in Ahnlich."""

    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    document_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="pdf")
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Nullable so existing rows and personal (non-matter) uploads keep working.
    # Set when a document is filed under a matter workspace (BE2, §3.1).
    matter_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "user_id": self.user_id,
            "document_name": self.document_name,
            "source_type": self.source_type,
            "page_count": self.page_count,
            "chunk_count": self.chunk_count,
            "file_size_bytes": self.file_size_bytes,
            "matter_id": self.matter_id,
            "uploaded_at": self.uploaded_at,
        }


# ---------------------------------------------------------------------------
# Platform / chambers schema (BE2, plan §3.1)
#
# All tables live on the shared ``Base`` so the existing
# ``Base.metadata.create_all`` call (in PostgresDocumentRegistry.initialize and
# db.session.init_models) provisions them automatically — no separate migration
# tool is wired in today (see db/session.py for the rationale). Relationships
# are enforced in application code rather than via hard FK constraints, which
# keeps create_all ordering and the delete-my-data erasure path simple.
# ---------------------------------------------------------------------------


class UserProfile(Base):
    """One row per Clerk user — the onboarding + jurisdiction record."""

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)  # Clerk sub
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="ASSOCIATE")
    nba_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chambers_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    default_jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False, default="NG")
    onboarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role,
            "nba_number": self.nba_number,
            "chambers_id": self.chambers_id,
            "default_jurisdiction": self.default_jurisdiction,
            "onboarded_at": _iso(self.onboarded_at),
            "updated_at": _iso(self.updated_at),
        }


class Chambers(Base):
    """A law firm / set of chambers — the team-account root."""

    __tablename__ = "chambers"

    chambers_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_tier: Mapped[str] = mapped_column(String(16), nullable=False, default="FREE")
    invite_code: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # P4 moat: Enterprise data-residency + custom retention (nullable = default).
    data_region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chambers_id": self.chambers_id,
            "name": self.name,
            "subscription_tier": self.subscription_tier,
            "invite_code": self.invite_code,
            "created_by_user_id": self.created_by_user_id,
            "data_region": self.data_region,
            "retention_days": self.retention_days,
            "created_at": _iso(self.created_at),
        }


class ChambersMembership(Base):
    """Join row: which users belong to which chambers, and in what role."""

    __tablename__ = "chambers_memberships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chambers_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="ASSOCIATE")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chambers_id": self.chambers_id,
            "user_id": self.user_id,
            "role": self.role,
            "status": self.status,
            "created_at": _iso(self.created_at),
        }


class Matter(Base):
    """A case / matter — the workspace documents and chats are scoped to."""

    __tablename__ = "matters"

    matter_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chambers_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    practice_area: Mapped[str] = mapped_column(String(32), nullable=False, default="OTHER")
    jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False, default="NG")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "matter_id": self.matter_id,
            "chambers_id": self.chambers_id,
            "created_by_user_id": self.created_by_user_id,
            "title": self.title,
            "client_name": self.client_name,
            "practice_area": self.practice_area,
            "jurisdiction": self.jurisdiction,
            "status": self.status,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


class Subscription(Base):
    """Billing record for a chambers (period + external Paystack/Stripe ref)."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chambers_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False, default="FREE")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chambers_id": self.chambers_id,
            "tier": self.tier,
            "status": self.status,
            "period_start": _iso(self.period_start),
            "period_end": _iso(self.period_end),
            "external_ref": self.external_ref,
            "created_at": _iso(self.created_at),
        }


class UsageEvent(Base):
    """Append-only meter for volume-based billing (QUERY/DOC_UPLOAD/EXPORT/AUDIO_MIN)."""

    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chambers_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chambers_id": self.chambers_id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "quantity": self.quantity,
            "created_at": _iso(self.created_at),
        }


class AuditLog(Base):
    """Who asked what, when, which docs — compliance + Enterprise audit trail."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    chambers_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    matter_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chambers_id": self.chambers_id,
            "user_id": self.user_id,
            "action": self.action,
            "matter_id": self.matter_id,
            "detail": self.detail or {},
            "created_at": _iso(self.created_at),
        }
