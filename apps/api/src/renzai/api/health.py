"""Foundation operational endpoints only."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from renzai.infrastructure.observability.metrics import set_readiness

router = APIRouter(tags=["operations"])


@router.get("/health", summary="Process liveness")
async def health() -> dict[str, str]:
    """Return liveness only; do not disclose dependency topology."""
    return {"status": "ok"}


@router.get("/ready", summary="Safe traffic readiness")
async def readiness(request: Request, response: Response) -> dict[str, str]:
    dependencies = request.app.state.dependencies
    ready = await dependencies.is_ready()
    set_readiness(ready)
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ready"}
