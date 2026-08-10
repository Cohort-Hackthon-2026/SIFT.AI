"""Per-user rate limiting.

A lightweight in-process sliding-window limiter keyed by the verified Clerk
user id. Applied to the abusable/expensive endpoints (chat stream, upload,
search) as a FastAPI dependency that also carries the authenticated user id
through, so those routes get auth + limiting in one dependency.

Scope note: state lives in this process only. For a multi-worker/multi-replica
deployment, back this with Redis (there's already a REDIS_URL in config) so the
window is shared. This in-memory version is correct for a single worker and is
the right first step; swapping the store is a localized change.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.auth import get_current_user_id
from app.config import get_settings


class SlidingWindowRateLimiter:
    """Fixed-capacity sliding window: at most ``limit`` hits per ``window`` seconds."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: float = 60.0) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        hits = self._hits[key]
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


# Module-level singleton so all requests in this worker share one window.
_limiter = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _limiter


async def rate_limited_user_id(
    user_id: str = Depends(get_current_user_id),
) -> str:
    """Auth + per-user rate limit in one dependency.

    Returns the authenticated user id (like ``get_current_user_id``) but first
    enforces the per-minute quota, raising 429 when exceeded. Disabled entirely
    when ``RATE_LIMIT_ENABLED`` is false.
    """
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED:
        return user_id

    if not _limiter.allow(user_id, settings.RATE_LIMIT_PER_MINUTE):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded ({settings.RATE_LIMIT_PER_MINUTE} requests/min). "
                "Please slow down and try again shortly."
            ),
            headers={"Retry-After": "60"},
        )
    return user_id
