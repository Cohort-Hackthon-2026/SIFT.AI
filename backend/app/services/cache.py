from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Protocol

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 300


class SearchCacheProtocol(Protocol):
    async def get(self, cache_key: str) -> list[dict[str, Any]] | None: ...

    async def set(self, cache_key: str, value: list[dict[str, Any]]) -> None: ...


def build_cache_key(query: str, user_id: str | None, document_id: str | None, top_k: int) -> str:
    """Deterministic key so identical strict-search requests hit the cache."""
    raw = f"{query.strip().lower()}|{user_id or ''}|{document_id or ''}|{top_k}"
    return "search:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class NoopSearchCache:
    """Used when REDIS_URL is not configured or Redis is unreachable."""

    async def get(self, cache_key: str) -> list[dict[str, Any]] | None:
        return None

    async def set(self, cache_key: str, value: list[dict[str, Any]]) -> None:
        return None


class RedisSearchCache:
    def __init__(self, redis_url: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._redis_url = redis_url
        self._ttl_seconds = ttl_seconds
        self._client = None
        self._last_error: str | None = None

    def _get_client(self):
        if self._client is None:
            import redis.asyncio as redis

            self._client = redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def get(self, cache_key: str) -> list[dict[str, Any]] | None:
        try:
            client = self._get_client()
            cached = await client.get(cache_key)
            if cached is None:
                return None
            return json.loads(cached)
        except Exception as exc:  # pragma: no cover - depends on live Redis availability
            self._last_error = f"{type(exc).__name__}: {exc}"
            logger.warning(f"SearchCache read failed, bypassing cache: {self._last_error}")
            return None

    async def set(self, cache_key: str, value: list[dict[str, Any]]) -> None:
        try:
            client = self._get_client()
            await client.set(cache_key, json.dumps(value), ex=self._ttl_seconds)
        except Exception as exc:  # pragma: no cover - depends on live Redis availability
            self._last_error = f"{type(exc).__name__}: {exc}"
            logger.warning(f"SearchCache write failed, skipping cache: {self._last_error}")


def create_search_cache() -> SearchCacheProtocol:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return NoopSearchCache()

    try:
        import redis.asyncio  # noqa: F401
    except ImportError:
        logger.warning("REDIS_URL is set but the `redis` package is not installed; caching disabled.")
        return NoopSearchCache()

    ttl_seconds = int(os.getenv("SEARCH_CACHE_TTL_SECONDS", str(DEFAULT_TTL_SECONDS)))
    return RedisSearchCache(redis_url, ttl_seconds=ttl_seconds)
