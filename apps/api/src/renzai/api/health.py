"""Foundation operational endpoints only."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

router = APIRouter(tags=["operations"])


@router.get("/health", summary="Process liveness")
async def health() -> dict[str, str]:
    """Return liveness only; do not disclose dependency topology."""
    return {"status": "ok"}


@router.get("/ready", summary="Safe traffic readiness")
async def readiness(request: Request, response: Response) -> dict[str, str]:
    dependencies = request.app.state.dependencies
    if not await dependencies.is_ready():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ready"}
