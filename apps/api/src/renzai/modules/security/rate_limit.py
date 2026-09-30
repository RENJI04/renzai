"""Analyze rate-limit adapters keyed only by a keyed, scoped identifier."""

from __future__ import annotations

from renzai.infrastructure.redis.client import RedisClient
from renzai.modules.auth.rate_limit import InMemoryAuthRateLimiter


class RedisAnalyzeRateLimiter:
    def __init__(self, redis: RedisClient, requests: int, window_seconds: int) -> None:
        self._redis = redis
        self._requests = requests
        self._window_seconds = window_seconds

    async def check(self, bucket: str) -> None:
        from renzai.core.errors import RateLimitError

        count = await self._redis.increment_window(
            f"renzai:analyze-rate:v1:{bucket}", self._window_seconds
        )
        if count is None or count > self._requests:
            raise RateLimitError()


class InMemoryAnalyzeRateLimiter(InMemoryAuthRateLimiter):
    """Test-only adapter with the same deterministic fixed-window semantics."""
