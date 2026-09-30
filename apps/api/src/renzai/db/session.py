"""Async engine/session lifecycle, intentionally without product tables."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from renzai.core.config import DatabaseConfig


class Database:
    def __init__(self, config: DatabaseConfig) -> None:
        engine_options: dict[str, int | bool] = {"pool_pre_ping": True}
        if not config.url.startswith("sqlite+"):
            engine_options.update(pool_size=config.pool_size, max_overflow=config.max_overflow)
        self._engine: AsyncEngine = create_async_engine(config.url, **engine_options)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessions() as session:
            yield session

    async def ping(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    async def close(self) -> None:
        await self._engine.dispose()
