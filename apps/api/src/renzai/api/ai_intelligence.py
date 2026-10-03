"""Tenant-scoped optional AI intelligence configuration and incident APIs."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    Principal,
    TenantPrincipal,
    csrf_principal,
    get_db,
    tenant_principal,
)
from renzai.modules.ai_intelligence.application import (
    AIConfigurationService,
    AIIntelligenceService,
    config_view,
)
from renzai.modules.ai_intelligence.domain import AITaskType, DisclosureMode

router = APIRouter(tags=["ai-intelligence"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AIConfigurationCreate(StrictModel):
    application_id: UUID | None = None
    environment_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["openai_compatible_remote", "openai_compatible_local"]
    base_url: str = Field(min_length=1, max_length=512)
    model: str = Field(min_length=1, max_length=160)
    credential: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    allow_full_content: bool = False
    connect_timeout_seconds: int = Field(default=3, ge=1, le=10)
    request_timeout_seconds: int = Field(default=30, ge=1, le=120)
    response_max_bytes: int = Field(default=64 * 1024, ge=1024, le=128 * 1024)


class AIConfigurationUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=160)
    credential: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    allow_full_content: bool | None = None


class AIIntelligenceCreate(StrictModel):
    task_type: AITaskType
    disclosure_mode: DisclosureMode = DisclosureMode.REDACTED


def _config_service(request: Request, db: AsyncSession) -> AIConfigurationService:
    dependencies = request.app.state.dependencies
    return AIConfigurationService(
        db,
        dependencies.ai_credential_key_ring,
        dependencies.outbound_target_guard,
        dependencies.ai_intelligence_provider,
    )


@router.post("/organizations/{organization_id}/ai-providers", status_code=status.HTTP_201_CREATED)
async def create_ai_provider(
    request: Request,
    body: AIConfigurationCreate,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    row = await _config_service(request, db).create(
        tenant.membership,
        tenant.principal.user,
        application_id=body.application_id,
        environment_id=body.environment_id,
        name=body.name,
        kind=body.kind,
        base_url=body.base_url,
        model=body.model,
        credential=body.credential.get_secret_value() if body.credential else None,
        allow_full_content=body.allow_full_content,
        connect_timeout_seconds=body.connect_timeout_seconds,
        request_timeout_seconds=body.request_timeout_seconds,
        response_max_bytes=body.response_max_bytes,
    )
    return config_view(row)


@router.get("/organizations/{organization_id}/ai-providers")
async def list_ai_providers(
    organization_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return {
        "items": [
            config_view(row) for row in await _config_service(request, db).list(organization_id)
        ]
    }


@router.get("/organizations/{organization_id}/ai-providers/{config_id}")
async def get_ai_provider(
    organization_id: UUID,
    config_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return config_view(await _config_service(request, db).get(organization_id, config_id))


@router.patch("/organizations/{organization_id}/ai-providers/{config_id}")
async def update_ai_provider(
    request: Request,
    organization_id: UUID,
    config_id: UUID,
    body: AIConfigurationUpdate,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = _config_service(request, db)
    row = await service.get(organization_id, config_id)
    return config_view(
        await service.update(
            tenant.membership,
            tenant.principal.user,
            row,
            name=body.name,
            model=body.model,
            credential=body.credential.get_secret_value() if body.credential else None,
            allow_full_content=body.allow_full_content,
        )
    )


@router.post("/organizations/{organization_id}/ai-providers/{config_id}/{operation}")
async def change_ai_provider(
    request: Request,
    organization_id: UUID,
    config_id: UUID,
    operation: Literal["enable", "disable", "validate"],
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = _config_service(request, db)
    row = await service.get(organization_id, config_id)
    if operation == "validate":
        await service.validate_connection(tenant.membership, tenant.principal.user, row)
    else:
        row = await service.set_enabled(
            tenant.membership, tenant.principal.user, row, operation == "enable"
        )
    return config_view(row)


@router.post(
    "/organizations/{organization_id}/incidents/{incident_id}/ai-analysis",
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_ai_intelligence(
    request: Request,
    organization_id: UUID,
    incident_id: UUID,
    body: AIIntelligenceCreate,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, object]:
    service = AIIntelligenceService(db)
    row = await service.request(
        tenant.membership,
        tenant.principal.user,
        incident_id,
        task_type=body.task_type,
        disclosure_mode=body.disclosure_mode,
        idempotency_key=idempotency_key,
    )
    if row.status == "pending":
        try:
            request.app.state.dependencies.ai_task_dispatcher.enqueue(
                organization_id, row.request_id
            )
        except Exception:
            await service.mark_dispatch_failed(organization_id, row.request_id)
    return await service.get(organization_id, row.request_id)


@router.get("/organizations/{organization_id}/incidents/{incident_id}/ai-analysis")
async def list_ai_intelligence(
    organization_id: UUID,
    incident_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return {
        "items": await AIIntelligenceService(db).list_for_incident(organization_id, incident_id)
    }


@router.get("/organizations/{organization_id}/ai-analysis/{request_id}")
async def get_ai_intelligence(
    organization_id: UUID,
    request_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return await AIIntelligenceService(db).get(organization_id, request_id)
