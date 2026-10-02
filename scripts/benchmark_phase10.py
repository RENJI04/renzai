"""Benchmark Phase 10 dashboard aggregation on an explicit disposable PostgreSQL database."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from statistics import median, quantiles
from time import perf_counter
from uuid import UUID

from sqlalchemy import delete, insert, text

from renzai.core.config import DatabaseConfig
from renzai.core.ids import new_uuid7
from renzai.db import models as _models  # noqa: F401
from renzai.db.session import Database
from renzai.modules.analytics.application import AnalyticsService
from renzai.modules.analytics.domain import AnalyticsWindow
from renzai.modules.applications.models import Application
from renzai.modules.environments.models import Environment
from renzai.modules.organizations.models import Organization
from renzai.modules.security.models import AnalysisResult, SecurityEvent

ROUNDS = 12


async def main() -> None:
    database_url = os.environ.get("RENZAI_TEST_DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql+asyncpg://"):
        raise SystemExit(
            "Set RENZAI_TEST_DATABASE_URL to a disposable asyncpg PostgreSQL database."
        )
    database = Database(DatabaseConfig(url=database_url, pool_size=2, max_overflow=0))
    organization_id = new_uuid7()
    application_id = new_uuid7()
    environment_id = new_uuid7()
    as_of = datetime.now(UTC).replace(microsecond=0)
    try:
        async with database.session() as session:
            version = str(await session.scalar(text("SHOW server_version")))
            session.add(
                Organization(
                    organization_id=organization_id,
                    name="Phase 10 benchmark",
                    slug=f"phase10-bench-{str(organization_id)[:12]}",
                    settings={"audit_retention_days": 365},
                )
            )
            await session.flush()
            session.add(
                Application(
                    application_id=application_id,
                    organization_id=organization_id,
                    name="Benchmark",
                    name_key="benchmark",
                )
            )
            await session.flush()
            session.add(
                Environment(
                    environment_id=environment_id,
                    organization_id=organization_id,
                    application_id=application_id,
                    type="production",
                )
            )
            await session.commit()

        print(f"PostgreSQL {version}")
        previous = 0
        for size in (1_000, 10_000):
            await seed(
                database,
                organization_id,
                application_id,
                environment_id,
                as_of,
                start=previous,
                stop=size,
            )
            previous = size
            samples = await measure(database, organization_id, as_of)
            print(
                f"{size:,} analyses: median={median(samples):.2f} ms "
                f"p95={quantiles(samples, n=100, method='inclusive')[94]:.2f} ms "
                f"runs={ROUNDS}"
            )

        async with database.session() as session:
            plan = (
                await session.execute(
                    text(
                        "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
                        "SELECT count(ar.analysis_id) FROM security_events se "
                        "JOIN analysis_results ar ON ar.event_id = se.event_id "
                        "WHERE se.organization_id = :organization_id "
                        "AND se.occurred_at >= :window_start "
                        "AND se.occurred_at <= :window_end "
                        "AND ar.status = 'completed'"
                    ),
                    {
                        "organization_id": organization_id,
                        "window_start": as_of - timedelta(days=89),
                        "window_end": as_of,
                    },
                )
            ).scalars()
            print("\nCore summary EXPLAIN ANALYZE:")
            print("\n".join(str(line) for line in plan))
    finally:
        async with database.session() as cleanup:
            await cleanup.execute(
                delete(Organization).where(Organization.organization_id == organization_id)
            )
            await cleanup.commit()
        await database.close()


async def seed(
    database: Database,
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    as_of: datetime,
    *,
    start: int,
    stop: int,
) -> None:
    event_rows: list[dict[str, object]] = []
    analysis_rows: list[dict[str, object]] = []
    for index in range(start, stop):
        event_id = new_uuid7()
        analysis_id = new_uuid7()
        threat = index % 5 == 0
        occurred_at = as_of - timedelta(minutes=index % (89 * 24 * 60))
        event_rows.append(
            {
                "event_id": event_id,
                "organization_id": organization_id,
                "application_id": application_id,
                "environment_id": environment_id,
                "direction": "input",
                "source": "analyze",
                "occurred_at": occurred_at,
                "correlation_id": f"benchmark-{index}",
                "privacy_mode": "METADATA_ONLY",
                "content": None,
                "content_bytes": 0,
                "retention_days": 90,
                "action": "block" if threat else "allow",
                "risk_score": 75 if threat else 0,
                "risk_severity": "high" if threat else "low",
            }
        )
        analysis_rows.append(
            {
                "analysis_id": analysis_id,
                "event_id": event_id,
                "completed_at": occurred_at,
                "normalization_version": "1.0.0",
                "ruleset_version": "1.0.0",
                "status": "completed",
                "finding_count": 1 if threat else 0,
                "normalization_ms": 1,
                "detector_ms": 1,
                "total_ms": 2,
                "capabilities": {},
                "risk_score": 75 if threat else 0,
                "risk_severity": "high" if threat else "low",
                "risk_confidence": 90,
                "base_score": 75 if threat else 0,
                "corroboration_bonus": 0,
                "critical_floor": 0,
                "action": "block" if threat else "allow",
                "risk_ms": 0,
                "policy_ms": 0,
            }
        )
    async with database.session() as session:
        await session.execute(insert(SecurityEvent), event_rows)
        await session.execute(insert(AnalysisResult), analysis_rows)
        await session.commit()


async def measure(database: Database, organization_id: UUID, as_of: datetime) -> list[float]:
    async def once() -> float:
        async with database.session() as session:
            started = perf_counter()
            result = await AnalyticsService(session, as_of=as_of).dashboard(
                organization_id, window=AnalyticsWindow.DAYS_90
            )
            elapsed = (perf_counter() - started) * 1_000
            assert result["summary"]
            return elapsed

    await once()
    return [await once() for _ in range(ROUNDS)]


if __name__ == "__main__":
    asyncio.run(main())
