"""Per-client rate limit for endpoints that call an LLM (in-memory sliding window).

In-process state is enough for this single-instance app; a multi-instance deployment would
move the window to Redis. Clients are keyed by IP address: the socket peer, or, behind a
trusted reverse proxy (TRUST_PROXY), the X-Forwarded-For entry that proxy appended.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings


class SlidingWindowLimiter:
    """At most `limit` hits per key in any `window_seconds` period."""

    def __init__(
        self, limit: int, window_seconds: float = 60.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float | None:
        """Record a hit; return None if allowed, else seconds until the next one is allowed."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                return hits[0] + self.window_seconds - now
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter: SlidingWindowLimiter | None = None


def get_limiter() -> SlidingWindowLimiter:
    global _limiter
    limit = get_settings().rate_limit_per_minute
    if _limiter is None or _limiter.limit != limit:
        _limiter = SlidingWindowLimiter(limit)
    return _limiter


def forwarded_client(header: str, trusted_hops: int) -> str | None:
    """The address appended by the outermost trusted proxy.

    Each proxy appends the peer it saw, so the last `trusted_hops` entries were written by our
    proxies and everything to their left is whatever the client sent (forgeable). With fewer
    entries than hops, the left-most one is the best we have.
    """
    entries = [entry.strip() for entry in header.split(",") if entry.strip()]
    if not entries:
        return None
    return entries[-trusted_hops] if len(entries) >= trusted_hops else entries[0]


def client_ip(request: Request, settings: Settings) -> str:
    """Rate-limit key: X-Forwarded-For only when we sit behind a proxy we trust."""
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            address = forwarded_client(forwarded, settings.trusted_proxy_count)
            if address:
                return address
    return request.client.host if request.client else "unknown"


def llm_rate_limit(request: Request) -> None:
    """FastAPI dependency: 429 with a clear message once a client exceeds the LLM limit."""
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    retry_after = get_limiter().hit(client_ip(request, settings))
    if retry_after is None:
        return
    seconds = max(1, math.ceil(retry_after))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            f"Too many AI requests: the limit is {settings.rate_limit_per_minute} per minute. "
            f"Try again in {seconds} s."
        ),
        headers={"Retry-After": str(seconds)},
    )


# Use as `dependencies=[LlmRateLimit]` on every route that can call an LLM.
LlmRateLimit = Depends(llm_rate_limit)
