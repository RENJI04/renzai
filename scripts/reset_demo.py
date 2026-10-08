"""Remove only the exactly marked Renzai Phase 16 demo tenant."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
API_SOURCE = ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SOURCE))

from renzai.core.config import Settings  # noqa: E402
from renzai.db.session import Database  # noqa: E402
from renzai.demo import DemoSafetyError, reset_demo  # noqa: E402


async def _run() -> int:
    database = Database(Settings().database)
    try:
        async with database.session() as session:
            removed = await reset_demo(session)
    except DemoSafetyError as error:
        print(f"Demo reset refused: {error}", file=sys.stderr)
        return 2
    finally:
        await database.close()
    print("Renzai demo tenant removed." if removed else "No Renzai demo tenant was present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
