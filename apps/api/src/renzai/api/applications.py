"""Session-authenticated Application, Environment and API-key endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    Principal,
    TenantPrincipal,
    csrf_principal,
    get_application_key_crypto,
    get_db,
    tenant_principal,
)
from renzai.core.config import PrivacyMode
from renzai.infrastructure.crypto.application_keys import ApplicationKeyCrypto
from renzai.modules.api_keys.models import ApplicationApiKey
from renzai.modules.applications.application import ApplicationService
from renzai.modules.applications.models import Application
from renzai.modules.environments.models import Environment
from renzai.modules.policies.application import bootstrap_application_baseline

router = APIRouter(tags=["applications"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApplicationCreateRequest(StrictModel):
    name: str = Field(min_length=2, max_length=120)


class ApplicationUpdateRequest(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    privacy_mode: PrivacyMode | None = None
    safe_content_persistence: bool | None = None
    security_retention_days: int | None = Field(default=None, ge=1, le=365)


class EnvironmentCreateRequest(StrictModel):
    type: Literal["development", "staging", "production"]


class EnvironmentUpdateRequest(StrictModel):
    status: Literal["active", "disabled"]


class KeyCreateRequest(StrictModel):
    label: str = Field(min_length=1, max_length=80)
    expires_at: datetime | None = None


class KeyRotateRequest(StrictModel):
    expires_at: datetime | None = None


def _service(
    request: Request, db: AsyncSession, key_crypto: ApplicationKeyCrypto
) -> ApplicationService:
    settings = request.app.state.settings
    return ApplicationService(
        db,
        key_crypto,
        settings.privacy.default_mode,
        settings.privacy.persist_safe_content,
        settings.retention.security_days,
        settings.application_keys.maximum_expiry_days,
    )


@router.post("/organizations/{organization_id}/applications", status_code=status.HTTP_201_CREATED)
async def create_application(
    body: ApplicationCreateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    application = await service.create_application(
        tenant.membership, tenant.principal.user, body.name, commit=False
    )
    await bootstrap_application_baseline(
        db, application, actor_user_id=tenant.principal.user.user_id
    )
    await service.commit_conflict(["name", "priority"])
    return _application_view(application)


@router.get("/organizations/{organization_id}/applications")
async def list_applications(
    organization_id: UUID,
    request: Request,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    rows = await _service(request, db, key_crypto).list_applications(organization_id)
    return {"items": [_application_view(row) for row in rows]}


@router.get("/organizations/{organization_id}/applications/{application_id}")
async def get_application(
    organization_id: UUID,
    application_id: UUID,
    request: Request,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    application = await _service(request, db, key_crypto).application(
        organization_id, application_id
    )
    return _application_view(application)


@router.patch("/organizations/{organization_id}/applications/{application_id}")
async def update_application(
    organization_id: UUID,
    application_id: UUID,
    body: ApplicationUpdateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    application = await service.application(organization_id, application_id)
    updated = await service.update_application(
        tenant.membership,
        tenant.principal.user,
        application,
        name=body.name,
        privacy_mode=body.privacy_mode,
        safe_content_persistence=body.safe_content_persistence,
        security_retention_days=body.security_retention_days,
    )
    return _application_view(updated)


@router.post("/organizations/{organization_id}/applications/{application_id}/archive")
async def archive_application(
    organization_id: UUID,
    application_id: UUID,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    application = await service.application(organization_id, application_id)
    archived = await service.archive_application(
        tenant.membership, tenant.principal.user, application
    )
    return _application_view(archived)


@router.post(
    "/organizations/{organization_id}/applications/{application_id}/environments",
    status_code=status.HTTP_201_CREATED,
)
async def create_environment(
    organization_id: UUID,
    application_id: UUID,
    body: EnvironmentCreateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    application = await service.application(organization_id, application_id)
    environment = await service.create_environment(
        tenant.membership, tenant.principal.user, application, body.type
    )
    return _environment_view(environment)


@router.get("/organizations/{organization_id}/applications/{application_id}/environments")
async def list_environments(
    organization_id: UUID,
    application_id: UUID,
    request: Request,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    await service.application(organization_id, application_id)
    rows = await service.list_environments(organization_id, application_id)
    return {"items": [_environment_view(row) for row in rows]}


@router.patch(
    "/organizations/{organization_id}/applications/{application_id}/environments/{environment_id}"
)
async def update_environment(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    body: EnvironmentUpdateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    environment = await service.environment(organization_id, application_id, environment_id)
    updated = await service.update_environment(
        tenant.membership, tenant.principal.user, environment, body.status
    )
    return _environment_view(updated)


@router.post(
    "/organizations/{organization_id}/applications/{application_id}/environments/{environment_id}/keys",
    status_code=status.HTTP_201_CREATED,
)
async def create_key(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    body: KeyCreateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    application = await service.application(organization_id, application_id)
    environment = await service.environment(organization_id, application_id, environment_id)
    key, secret = await service.issue_key(
        tenant.membership,
        tenant.principal.user,
        application,
        environment,
        body.label,
        body.expires_at,
    )
    return {"secret_once": secret, "metadata": _key_view(key)}


@router.get(
    "/organizations/{organization_id}/applications/{application_id}/environments/{environment_id}/keys"
)
async def list_keys(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    request: Request,
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    service._require_editor(tenant.membership)
    await service.environment(organization_id, application_id, environment_id)
    rows = await service.list_keys(organization_id, application_id, environment_id)
    return {"items": [_key_view(row) for row in rows]}


@router.post(
    "/organizations/{organization_id}/applications/{application_id}/environments/{environment_id}/keys/{key_id}/revoke"
)
async def revoke_key(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    key_id: UUID,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    key = await service.key(organization_id, application_id, environment_id, key_id)
    return _key_view(await service.revoke_key(tenant.membership, tenant.principal.user, key))


@router.post(
    "/organizations/{organization_id}/applications/{application_id}/environments/{environment_id}/keys/{key_id}/rotate"
)
async def rotate_key(
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    key_id: UUID,
    body: KeyRotateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    service = _service(request, db, key_crypto)
    application = await service.application(organization_id, application_id)
    environment = await service.environment(organization_id, application_id, environment_id)
    key = await service.key(organization_id, application_id, environment_id, key_id)
    replacement, secret = await service.rotate_key(
        tenant.membership,
        tenant.principal.user,
        application,
        environment,
        key,
        body.expires_at,
    )
    return {"secret_once": secret, "metadata": _key_view(replacement)}


def _application_view(application: Application) -> dict[str, object]:
    return {
        "application_id": str(application.application_id),
        "organization_id": str(application.organization_id),
        "name": application.name,
        "status": application.status,
        "privacy_mode": application.privacy_mode,
        "safe_content_persistence": application.safe_content_persistence,
        "security_retention_days": application.security_retention_days,
        "created_at": application.created_at.isoformat(),
        "updated_at": application.updated_at.isoformat(),
    }


def _environment_view(environment: Environment) -> dict[str, object]:
    return {
        "environment_id": str(environment.environment_id),
        "application_id": str(environment.application_id),
        "organization_id": str(environment.organization_id),
        "type": environment.type,
        "status": environment.status,
        "created_at": environment.created_at.isoformat(),
        "updated_at": environment.updated_at.isoformat(),
    }


def _key_view(key: ApplicationApiKey) -> dict[str, object]:
    return {
        "key_id": str(key.key_id),
        "label": key.label,
        "prefix": key.prefix,
        "created_at": key.created_at.isoformat(),
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "verifier_key_id": key.verifier_key_id,
    }
