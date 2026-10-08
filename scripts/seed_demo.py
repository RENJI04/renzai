"""Seed the opt-in synthetic Renzai demonstration tenant."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
API_SOURCE = ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SOURCE))

from renzai.core.config import Settings  # noqa: E402
from renzai.db.session import Database  # noqa: E402
from renzai.demo import DemoSafetyError, seed_demo  # noqa: E402


async def _run(owner_email: str) -> int:
    database = Database(Settings().database)
    try:
        async with database.session() as session:
            summary = await seed_demo(session, owner_email=owner_email)
    except DemoSafetyError as error:
        print(f"Demo seed refused: {error}", file=sys.stderr)
        return 2
    finally:
        await database.close()
    state = "already present" if summary.already_present else "created"
    print(f"Renzai demo tenant {state}: {summary.organization_id}")
    print(
        f"applications={summary.applications} environments={summary.environments} "
        f"analyses={summary.analyses} incidents={summary.incidents} "
        f"provider_calls={summary.provider_calls} ai_results={summary.ai_results}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-email", default="analyst@demo.invalid")
    arguments = parser.parse_args()
    return asyncio.run(_run(arguments.owner_email))


if __name__ == "__main__":
    raise SystemExit(main())
