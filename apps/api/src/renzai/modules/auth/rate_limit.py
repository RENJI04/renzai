"""Authentication rate-limit application port and adapters."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from time import monotonic

from renzai.core.errors import RateLimitError
from renzai.infrastructure.redis.client import RedisClient


class RedisAuthRateLimiter:
    def __init__(self, redis: RedisClient, attempts: int, window_seconds: int) -> None:
        self._redis = redis
        self._attempts = attempts
        self._window_seconds = window_seconds

    async def check(self, bucket: str) -> None:
        count = await self._redis.increment_window(
            f"renzai:auth-rate:v1:{bucket}", self._window_seconds
        )
        if count is None or count > self._attempts:
            raise RateLimitError()


@dataclass(slots=True)
class _Window:
    count: int
    expires_at: float


class InMemoryAuthRateLimiter:
    """Deterministic test adapter; production uses Redis."""

    def __init__(self, attempts: int, window_seconds: int) -> None:
        self._attempts = attempts
        self._window_seconds = window_seconds
        self._windows: dict[str, _Window] = defaultdict(lambda: _Window(0, 0))
        self._lock = asyncio.Lock()

    async def check(self, bucket: str) -> None:
        async with self._lock:
            now = monotonic()
            window = self._windows[bucket]
            if window.expires_at <= now:
                window.count = 0
                window.expires_at = now + self._window_seconds
            window.count += 1
            if window.count > self._attempts:
                raise RateLimitError()
