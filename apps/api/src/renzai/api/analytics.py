"""Bounded tenant-scoped operational dashboard API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import TenantPrincipal, get_db, tenant_principal
from renzai.modules.analytics.application import AnalyticsService
from renzai.modules.analytics.domain import AnalyticsSource, AnalyticsWindow

router = APIRouter(tags=["analytics"])


@router.get("/organizations/{organization_id}/analytics/dashboard")
async def dashboard(
    organization_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    window: Annotated[AnalyticsWindow, Query()] = AnalyticsWindow.HOURS_24,
    application_id: UUID | None = None,
    environment_id: UUID | None = None,
    source: AnalyticsSource | None = None,
) -> dict[str, object]:
    return await AnalyticsService(db).dashboard(
        organization_id,
        window=window,
        application_id=application_id,
        environment_id=environment_id,
        source=source,
    )
