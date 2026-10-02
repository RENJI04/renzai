"""JSON-only worker tasks. AI jobs receive tenant/object IDs, never incident content."""
# mypy: disable-error-code=untyped-decorator

from __future__ import annotations

import asyncio
from uuid import UUID

from renzai.core.config import Settings
from renzai.core.lifecycle import build_runtime_dependencies
from renzai.modules.ai_intelligence.application import process_ai_request
from renzai_worker.celery_app import celery_app


@celery_app.task(name="renzai.diagnostics.echo_request_id")
def echo_request_id(request_id: str) -> dict[str, str]:
    return {"status": "ok", "request_id": request_id}


@celery_app.task(name="renzai.ai_intelligence.process", max_retries=0)
def process_ai_intelligence(organization_id: str, request_id: str) -> dict[str, str]:
    """Re-fetch an authorized tenant-scoped job and process it idempotently."""

    return asyncio.run(_process(UUID(organization_id), UUID(request_id)))


async def _process(organization_id: UUID, request_id: UUID) -> dict[str, str]:
    dependencies = build_runtime_dependencies(Settings())
    try:
        async with dependencies.database.session() as db:
            result = await process_ai_request(
                db,
                dependencies.ai_intelligence_provider,
                organization_id,
                request_id,
            )
            return {"status": result.status, "request_id": str(result.request_id)}
    finally:
        await dependencies.close()
