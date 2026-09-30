"""Owner/Admin provider configuration management with masked credential metadata."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    Principal,
    TenantPrincipal,
    csrf_principal,
    get_db,
    tenant_principal,
)
from renzai.modules.providers.application import ProviderService
from renzai.modules.providers.models import ProviderConfiguration

router = APIRouter(tags=["providers"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProviderCreateRequest(StrictModel):
    kind: Literal["openai_compatible_remote", "openai_compatible_local"]
    name: str = Field(min_length=2, max_length=120)
    base_url: str = Field(min_length=8, max_length=512)
    model: str = Field(min_length=1, max_length=160)
    credential: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    supports_seed: bool = False
    max_tokens: int = Field(default=4096, ge=1, le=4096)
    connect_timeout_seconds: int | None = Field(default=None, ge=1, le=10)
    chat_timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    health_timeout_seconds: int | None = Field(default=None, ge=1, le=15)
    response_max_bytes: int | None = Field(default=None, ge=1024, le=512 * 1024)


class ProviderUpdateRequest(StrictModel):
    kind: Literal["openai_compatible_remote", "openai_compatible_local"] | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    base_url: str | None = Field(default=None, min_length=8, max_length=512)
    model: str | None = Field(default=None, min_length=1, max_length=160)
    credential: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    supports_seed: bool | None = None
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    connect_timeout_seconds: int | None = Field(default=None, ge=1, le=10)
    chat_timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    health_timeout_seconds: int | None = Field(default=None, ge=1, le=15)
    response_max_bytes: int | None = Field(default=None, ge=1024, le=512 * 1024)


def _service(request: Request, db: AsyncSession) -> ProviderService:
    dependencies = request.app.state.dependencies
    return ProviderService(
        db,
        dependencies.provider_credential_key_ring,
        dependencies.outbound_target_guard,
        dependencies.chat_provider,
    )


@router.post(
    "/organizations/{organization_id}/applications/{application_id}/environments/"
    "{environment_id}/providers",
    status_code=status.HTTP_201_CREATED,
)
async def create_provider(
    application_id: UUID,
    environment_id: UUID,
    body: ProviderCreateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    defaults = request.app.state.settings.provider
    row = await _service(request, db).create(
        tenant.membership,
        tenant.principal.user,
        application_id=application_id,
        environment_id=environment_id,
        kind=body.kind,
        name=body.name,
        base_url=body.base_url,
        model=body.model,
        credential=body.credential.get_secret_value() if body.credential else None,
        supports_seed=body.supports_seed,
        max_tokens=body.max_tokens,
        connect_timeout_seconds=body.connect_timeout_seconds or defaults.connect_timeout_seconds,
        chat_timeout_seconds=body.chat_timeout_seconds or defaults.chat_timeout_seconds,
        health_timeout_seconds=body.health_timeout_seconds or defaults.health_timeout_seconds,
        response_max_bytes=body.response_max_bytes or defaults.response_max_bytes,
    )
    return _view(row)


@router.get(
    "/organizations/{organization_id}/applications/{application_id}/environments/"
    "{environment_id}/providers"
)
async def list_providers(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    request: Request,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    rows = await _service(request, db).list(organization_id, application_id, environment_id)
    return {"items": [_view(row) for row in rows]}


@router.get(
    "/organizations/{organization_id}/applications/{application_id}/environments/"
    "{environment_id}/providers/{provider_id}"
)
async def get_provider(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    provider_id: UUID,
    request: Request,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return _view(
        await _service(request, db).get(
            organization_id, application_id, environment_id, provider_id
        )
    )


@router.patch(
    "/organizations/{organization_id}/applications/{application_id}/environments/"
    "{environment_id}/providers/{provider_id}"
)
async def update_provider(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    provider_id: UUID,
    body: ProviderUpdateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = _service(request, db)
    row = await service.get(organization_id, application_id, environment_id, provider_id)
    return _view(
        await service.update(
            tenant.membership,
            tenant.principal.user,
            row,
            kind=body.kind,
            name=body.name,
            base_url=body.base_url,
            model=body.model,
            credential=body.credential.get_secret_value() if body.credential else None,
            supports_seed=body.supports_seed,
            max_tokens=body.max_tokens,
            connect_timeout_seconds=body.connect_timeout_seconds,
            chat_timeout_seconds=body.chat_timeout_seconds,
            health_timeout_seconds=body.health_timeout_seconds,
            response_max_bytes=body.response_max_bytes,
        )
    )


async def _state_change(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    provider_id: UUID,
    request: Request,
    tenant: TenantPrincipal,
    db: AsyncSession,
    enabled: bool,
) -> dict[str, object]:
    service = _service(request, db)
    row = await service.get(organization_id, application_id, environment_id, provider_id)
    return _view(
        await service.set_enabled(tenant.membership, tenant.principal.user, row, enabled=enabled)
    )


@router.post(
    "/organizations/{organization_id}/applications/{application_id}/environments/"
    "{environment_id}/providers/{provider_id}/enable"
)
async def enable_provider(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    provider_id: UUID,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return await _state_change(
        organization_id, application_id, environment_id, provider_id, request, tenant, db, True
    )


@router.post(
    "/organizations/{organization_id}/applications/{application_id}/environments/"
    "{environment_id}/providers/{provider_id}/disable"
)
async def disable_provider(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    provider_id: UUID,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return await _state_change(
        organization_id, application_id, environment_id, provider_id, request, tenant, db, False
    )


@router.post(
    "/organizations/{organization_id}/applications/{application_id}/environments/"
    "{environment_id}/providers/{provider_id}/validate"
)
async def validate_provider(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    provider_id: UUID,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = _service(request, db)
    row = await service.get(organization_id, application_id, environment_id, provider_id)
    return _view(
        await service.validate_configuration(tenant.membership, tenant.principal.user, row)
    )


def _view(row: ProviderConfiguration) -> dict[str, object]:
    return {
        "provider_id": str(row.provider_id),
        "organization_id": str(row.organization_id),
        "application_id": str(row.application_id),
        "environment_id": str(row.environment_id),
        "kind": row.kind,
        "name": row.name,
        "base_url": row.base_url,
        "model": row.model,
        "credential_present": row.credential_ciphertext is not None,
        "credential_key_id": row.credential_key_id,
        "supports_seed": row.supports_seed,
        "max_tokens": row.max_tokens,
        "connect_timeout_seconds": row.connect_timeout_seconds,
        "chat_timeout_seconds": row.chat_timeout_seconds,
        "health_timeout_seconds": row.health_timeout_seconds,
        "response_max_bytes": row.response_max_bytes,
        "status": row.status,
        "last_validation_status": row.last_validation_status,
        "last_validated_at": row.last_validated_at.isoformat() if row.last_validated_at else None,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
