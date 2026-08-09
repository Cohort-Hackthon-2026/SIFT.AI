"""Tests for per-user rate limiting."""
from __future__ import annotations

import time

from app.rate_limit import SlidingWindowRateLimiter, get_rate_limiter


# ---------------------------------------------------------------------------
# SlidingWindowRateLimiter (pure unit)
# ---------------------------------------------------------------------------

def test_limiter_allows_up_to_limit_then_blocks() -> None:
    limiter = SlidingWindowRateLimiter()
    assert limiter.allow("user-a", limit=3) is True
    assert limiter.allow("user-a", limit=3) is True
    assert limiter.allow("user-a", limit=3) is True
    # 4th within the same window is rejected
    assert limiter.allow("user-a", limit=3) is False


def test_limiter_is_per_key() -> None:
    limiter = SlidingWindowRateLimiter()
    assert limiter.allow("user-a", limit=1) is True
    assert limiter.allow("user-a", limit=1) is False
    # A different user has an independent window
    assert limiter.allow("user-b", limit=1) is True


def test_limiter_window_expiry_frees_capacity() -> None:
    limiter = SlidingWindowRateLimiter()
    window = 0.05
    assert limiter.allow("user-a", limit=1, window_seconds=window) is True
    assert limiter.allow("user-a", limit=1, window_seconds=window) is False
    # Once the window elapses, the earlier hit is stale and capacity frees up.
    time.sleep(window + 0.02)
    assert limiter.allow("user-a", limit=1, window_seconds=window) is True


# ---------------------------------------------------------------------------
# Endpoint integration (429)
# ---------------------------------------------------------------------------

def test_search_endpoint_returns_429_over_limit(client, monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    get_rate_limiter().reset()

    payload = {"query": "termination clause", "top_k": 5}

    assert client.post("/api/v1/search/strict", json=payload).status_code == 200
    assert client.post("/api/v1/search/strict", json=payload).status_code == 200
    # Third request in the window is rejected.
    third = client.post("/api/v1/search/strict", json=payload)
    assert third.status_code == 429
    assert "Retry-After" in third.headers
