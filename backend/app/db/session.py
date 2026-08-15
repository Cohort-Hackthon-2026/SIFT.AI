"""Shared async SQLAlchemy session factory for the platform registries (BE2).

The original ``PostgresDocumentRegistry`` builds its own engine; rather than
spin up a fresh connection pool per new domain (profiles, chambers, matters,
billing, audit), they all share the single lazily-built engine here.

Migrations: this project has no dedicated migration tool wired in. Schema is
provisioned by ``Base.metadata.create_all`` (called from ``init_models`` and
from ``PostgresDocumentRegistry.initialize``), which issues ``CREATE TABLE IF
NOT EXISTS`` for every model on the shared ``Base``. New *tables* therefore
appear automatically on boot. Adding a *column* to an existing table is the one
case create_all does not handle — those are applied with an idempotent
``ALTER TABLE ... ADD COLUMN IF NOT EXISTS`` at the relevant registry's
``initialize`` (see chat_registry.matter_id). If the team later wants versioned
migrations, Alembic can be layered on top of these same models.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_engine = None
_sessionmaker = None
_last_error: str | None = None


def normalize_database_url(database_url: str) -> str:
    """SQLAlchemy's async engine needs an async dialect marker. Neon/plain
    ``postgresql://`` URLs would otherwise be opened with the sync psycopg2
    driver, so rewrite them to the psycopg (v3) async driver — matching the
    existing document registry's behaviour."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def database_configured() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def get_sessionmaker():
    """Return a shared ``async_sessionmaker`` bound to the app's Postgres, or
    ``None`` if the DB is not configured / SQLAlchemy async isn't importable.

    Never raises: callers treat ``None`` as "fall back to in-memory", matching
    the app-wide graceful-degradation philosophy.
    """
    global _engine, _sessionmaker, _last_error

    if _sessionmaker is not None:
        return _sessionmaker

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None

    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    except ImportError as exc:  # pragma: no cover - depends on install surface
        _last_error = f"{type(exc).__name__}: {exc}"
        logger.error("db.session: SQLAlchemy async not available: %s", _last_error)
        return None

    try:
        _engine = create_async_engine(normalize_database_url(database_url), pool_pre_ping=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
        return _sessionmaker
    except Exception as exc:  # pragma: no cover - depends on live DB availability
        _last_error = f"{type(exc).__name__}: {exc}"
        logger.error("db.session: failed to build engine: %s", _last_error)
        return None


async def init_models() -> None:
    """Create every table registered on ``Base`` (idempotent). No-op without a DB."""
    global _last_error
    sessionmaker = get_sessionmaker()
    if sessionmaker is None or _engine is None:
        return
    try:
        from app.db.models import Base

        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _last_error = None
    except Exception as exc:  # pragma: no cover - depends on live DB availability
        _last_error = f"{type(exc).__name__}: {exc}"
        logger.error("db.session: create_all failed: %s", _last_error)


def reset_for_tests() -> None:
    """Drop cached engine/sessionmaker so a test can reconfigure DATABASE_URL."""
    global _engine, _sessionmaker, _last_error
    _engine = None
    _sessionmaker = None
    _last_error = None
