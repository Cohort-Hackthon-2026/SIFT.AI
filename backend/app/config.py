"""Centralized application configuration.

Single source of truth for env-based settings plus a startup validator that
surfaces missing *critical* keys at boot (in the logs) instead of letting the
first chat request fail deep inside a stream.

Design note: services still read individual values via ``os.getenv`` at call
time so they can degrade gracefully and stay monkeypatch-friendly in tests.
This module does not replace that; it validates and documents the surface, and
gives ``main.py`` a single ``settings`` object + a ``log_startup_report()``.
"""
from __future__ import annotations

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    # LLM
    GEMINI_API_KEY: str | None = None
    DEFAULT_LLM_MODEL: str = "gemini-3.7-flash"

    # Web search
    EXA_API_KEY: str | None = None

    # Vector store (Ahnlich)
    AHNLICH_ENDPOINT: str | None = None
    AHNLICH_HOST: str | None = None
    AHNLICH_PORT: int | None = None
    USE_AHNLICH: bool = True
    AHNLICH_STORE_NAME: str = "legal_docs"

    # Persistence / infra
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None
    SEARCH_CACHE_TTL_SECONDS: int | None = None

    # PDF storage (Cloudflare R2)
    R2_ENDPOINT_URL: str | None = None
    R2_ACCESS_KEY_ID: str | None = None
    R2_SECRET_ACCESS_KEY: str | None = None
    R2_BUCKET_NAME: str = "sift-ai-pdfs"

    # Uploads
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024

    # HTTP / CORS
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate limiting (per authenticated user)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 30

    # Auth (Clerk)
    AUTH_ENABLED: bool = True
    CLERK_JWKS_URL: str | None = None
    CLERK_ISSUER: str | None = None
    CLERK_AUTHORIZED_PARTIES: str = ""

    # Billing (Paystack) — optional; checkout degrades to a mock when unset.
    PAYSTACK_SECRET_KEY: str | None = None
    PAYSTACK_PUBLIC_KEY: str | None = None
    PAYSTACK_CALLBACK_URL: str | None = None

    # Data residency (P4) — default region reported by the privacy endpoint.
    DEFAULT_DATA_REGION: str = "NG"

    def critical_warnings(self) -> list[str]:
        """Return human-readable warnings for missing keys that silently
        degrade core features. Never raises - this is advisory, matching the
        app's graceful-degradation philosophy."""
        warnings: list[str] = []
        if not self.GEMINI_API_KEY:
            warnings.append(
                "GEMINI_API_KEY is not set — chat synthesis will return a "
                "'service unavailable' message for every query."
            )
        if not self.EXA_API_KEY:
            warnings.append(
                "EXA_API_KEY is not set — ENHANCED mode will skip web search "
                "and answer from internal documents only."
            )
        if self.AUTH_ENABLED and not self.CLERK_JWKS_URL:
            warnings.append(
                "AUTH_ENABLED is true but CLERK_JWKS_URL is not set — every "
                "authenticated request will be rejected with 401. Set "
                "CLERK_JWKS_URL, or set AUTH_ENABLED=false for local dev."
            )
        if not self.DATABASE_URL:
            warnings.append(
                "DATABASE_URL is not set — using in-memory document/chat "
                "registries. Data will not survive a restart."
            )
        return warnings

    def log_startup_report(self) -> None:
        auth_state = "enabled (Clerk)" if self.AUTH_ENABLED else "DISABLED (local-dev-user)"
        logger.info(
            "SIFT.AI config: model=%s auth=%s vector=%s cache=%s storage=%s rate_limit=%s billing=%s",
            self.DEFAULT_LLM_MODEL,
            auth_state,
            "ahnlich" if (self.AHNLICH_ENDPOINT or self.AHNLICH_HOST) and self.USE_AHNLICH else "in-memory",
            "redis" if self.REDIS_URL else "disabled",
            "r2" if all([self.R2_ENDPOINT_URL, self.R2_ACCESS_KEY_ID, self.R2_SECRET_ACCESS_KEY]) else "noop",
            f"{self.RATE_LIMIT_PER_MINUTE}/min" if self.RATE_LIMIT_ENABLED else "disabled",
            "paystack" if self.PAYSTACK_SECRET_KEY else "mock",
        )
        for warning in self.critical_warnings():
            logger.warning("[config] %s", warning)


def get_settings() -> Settings:
    """Build a fresh Settings from the current environment.

    Not cached: tests (and the app itself) monkeypatch os.environ, and a
    fresh read keeps this consistent with the per-call os.getenv usage
    elsewhere in the codebase.
    """
    return Settings()
