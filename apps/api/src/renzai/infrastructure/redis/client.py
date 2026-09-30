"""Lazy async Redis adapter for future rate-limit and coordination ports."""

from __future__ import annotations

from redis.asyncio import Redis, from_url

from renzai.core.config import RedisConfig


class RedisClient:
    def __init__(self, config: RedisConfig) -> None:
        self._config = config
        self._client: Redis | None = None

    async def start(self) -> None:
        if self._client is None:
            self._client = from_url(self._config.url, decode_responses=True)  # type: ignore[no-untyped-call]

    async def ping(self) -> bool:
        try:
            await self.start()
            return bool(await self._client.ping()) if self._client else False
        except Exception:
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def increment_window(self, key: str, window_seconds: int) -> int | None:
        """Increment a fixed-window counter without exposing the original identifier."""
        try:
            await self.start()
            if self._client is None:
                return None
            async with self._client.pipeline(transaction=True) as pipeline:
                pipeline.incr(key)
                pipeline.expire(key, window_seconds, nx=True)
                count, _ = await pipeline.execute()
            return int(count)
        except Exception:
            return None
