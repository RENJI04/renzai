"""Machine-authenticated Analyze and session-authenticated Playground endpoints."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    ApplicationContext,
    Principal,
    TenantPrincipal,
    application_context,
    csrf_principal,
    get_application_key_crypto,
    get_db,
    tenant_principal,
)
from renzai.core.errors import AuthorizationError, InspectionFailureError, ValidationError
from renzai.infrastructure.crypto.application_keys import ApplicationKeyCrypto
from renzai.modules.applications.application import ApplicationService
from renzai.modules.memberships.domain import MembershipRole
from renzai.modules.security.application import AnalysisScope, AnalysisService
from renzai.modules.security.domain.normalization import NormalizationLimitError
from renzai.modules.security.domain.types import Direction, InspectionFailure

router = APIRouter(tags=["security"])
PLAYGROUND_ROLES = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
    MembershipRole.SECURITY_ANALYST,
    MembershipRole.DEVELOPER,
}


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    direction: Literal["input", "output"]
    content: str = Field(min_length=1)
    correlation_id: str | None = Field(default=None, min_length=1, max_length=128)
    metadata: (
        dict[
            Annotated[str, Field(min_length=1, max_length=64)],
            Annotated[str, Field(max_length=256)],
        ]
        | None
    ) = Field(default=None, max_length=16)


class PlaygroundRequest(AnalyzeRequest):
    application_id: UUID
    environment_id: UUID


def _validate_bytes(content: str, maximum: int) -> None:
    if len(content.encode("utf-8")) > maximum:
        raise ValidationError(details={"fields": ["content"]})


async def _run(
    request: Request,
    db: AsyncSession,
    body: AnalyzeRequest,
    scope: AnalysisScope,
    application: object,
    source: str,
) -> dict[str, object]:
    _validate_bytes(body.content, request.app.state.settings.analyze.max_text_bytes)
    try:
        return await AnalysisService(db).analyze(
            scope,
            application,  # type: ignore[arg-type]
            body.content,
            Direction(body.direction),
            source,
        )
    except (InspectionFailure, NormalizationLimitError) as error:
        await db.rollback()
        raise InspectionFailureError() from error
    except Exception:
        await db.rollback()
        raise


@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    request: Request,
    context: Annotated[ApplicationContext, Depends(application_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    bucket = key_crypto.rate_limit_identifier(str(context.key_id))
    await request.app.state.dependencies.analyze_rate_limiter.check(bucket)
    correlation_id = body.correlation_id or context.correlation_id
    return await _run(
        request,
        db,
        body,
        AnalysisScope(
            context.organization_id,
            context.application_id,
            context.environment_id,
            context.environment.type,
            correlation_id,
        ),
        context.application,
        "analyze",
    )


@router.post("/organizations/{organization_id}/playground/analyze")
async def playground_analyze(
    organization_id: UUID,
    body: PlaygroundRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    key_crypto: Annotated[ApplicationKeyCrypto, Depends(get_application_key_crypto)],
) -> dict[str, object]:
    if MembershipRole(tenant.membership.role) not in PLAYGROUND_ROLES:
        raise AuthorizationError()
    service = ApplicationService(
        db,
        key_crypto,
        request.app.state.settings.privacy.default_mode,
        request.app.state.settings.privacy.persist_safe_content,
        request.app.state.settings.retention.security_days,
        request.app.state.settings.application_keys.maximum_expiry_days,
    )
    application = await service.application(organization_id, body.application_id)
    environment = await service.environment(
        organization_id, body.application_id, body.environment_id
    )
    if application.status != "active" or environment.status != "active":
        raise AuthorizationError(details={"reason": "scope_inactive"})
    bucket = key_crypto.rate_limit_identifier(
        f"playground:{tenant.principal.user.user_id}:{environment.environment_id}"
    )
    await request.app.state.dependencies.analyze_rate_limiter.check(bucket)
    return await _run(
        request,
        db,
        body,
        AnalysisScope(
            organization_id,
            body.application_id,
            body.environment_id,
            environment.type,
            body.correlation_id or tenant.request_id or "unknown",
        ),
        application,
        "playground",
    )
