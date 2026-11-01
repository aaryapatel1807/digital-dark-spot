"""Tiny in-memory rate limiter for the expensive, unauthenticated endpoints.

Why: /api/fetch is an outbound fetch and /api/analyze can fan out to
20 fetches, all without authentication. With no limiter, one client
can turn the API into an open proxy / slow-URL battery. This is a
per-process, per-IP, fixed-window limiter — enough for a hackathon
demo and for this VM's single worker, and honest about its limits:

- It resets on restart and does not share state across workers, so
  it is NOT a production rate-limiting story (use a gateway/Redis
  counter there).
- Behind a proxy, every client shares the proxy's IP unless the
  deployment forwards a trusted client IP. This code deliberately
  does NOT trust X-Forwarded-For, because a client can spoof it.
- Health, sample, and the root endpoint are NOT limited: they are
  cheap and needed for liveness checks.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import HTTPException, Request

_LIMITS = {"fetch": 60, "analyze": 30, "discover": 30}  # requests per 60 seconds, per IP.
_WINDOW_SECONDS = 60.0

_lock = threading.Lock()
_buckets: dict[tuple[str, str], deque[float]] = {}


def _client_ip(request: Request) -> str:
    if request.client is not None:
        return request.client.host
    return "unknown"


def check_rate_limit(request: Request, endpoint: str) -> None:
    """Raise 429 when the caller's window for this endpoint is full."""
    now = time.monotonic()
    key = (_client_ip(request), endpoint)
    with _lock:
        bucket = _buckets.setdefault(key, deque())
        while bucket and bucket[0] <= now - _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _LIMITS[endpoint]:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for this endpoint. Wait a minute and try again.",
                headers={"Retry-After": "60"},
            )
        bucket.append(now)


def reset_rate_limits() -> None:
    """Test helper only. Clears all buckets."""
    with _lock:
        _buckets.clear()
