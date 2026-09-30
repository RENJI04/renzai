from __future__ import annotations

from renzai.core.config import DatabaseConfig
from renzai.core.ids import new_uuid7
from renzai.db.session import Database


def test_uuid7_is_a_database_compatible_uuid() -> None:
    identifier = new_uuid7()
    assert identifier.version == 7
    assert str(identifier) == str(identifier).lower()


async def test_async_database_foundation_can_ping_an_isolated_database() -> None:
    database = Database(DatabaseConfig(url="sqlite+aiosqlite://", pool_size=1, max_overflow=0))
    try:
        assert await database.ping() is True
    finally:
        await database.close()
