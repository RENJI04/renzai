"""Tenant-scoped incident queue, detail, and mutation APIs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    Principal,
    TenantPrincipal,
    csrf_principal,
    get_crypto,
    get_db,
    tenant_principal,
)
from renzai.core.errors import ValidationError
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.modules.incidents.application import IncidentService
from renzai.modules.incidents.domain import IncidentSeverity, IncidentStatus

router = APIRouter(tags=["incidents"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IncidentCreateRequest(StrictModel):
    application_id: UUID | None = None
    environment_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    severity: IncidentSeverity
    safe_summary: str | None = Field(default=None, min_length=1, max_length=500)


class IncidentStatusRequest(StrictModel):
    status: IncidentStatus
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    version: int = Field(ge=1)


class IncidentAssignmentRequest(StrictModel):
    assignee_user_id: UUID | None
    version: int = Field(ge=1)


class IncidentCommentRequest(StrictModel):
    body: str = Field(min_length=1, max_length=4000)


@router.get("/organizations/{organization_id}/incidents")
async def list_incidents(
    organization_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
    status_filter: Annotated[list[IncidentStatus] | None, Query(alias="status")] = None,
    severity: Annotated[list[IncidentSeverity] | None, Query()] = None,
    application_id: UUID | None = None,
    environment_id: UUID | None = None,
    assignee_user_id: UUID | None = None,
    unassigned: bool = False,
    source: Literal["manual", "gateway", "analyze", "playground"] | None = None,
    action: Literal["allow", "flag", "block", "redact", "require_review"] | None = None,
    category: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    created_from: Annotated[datetime | None, Query(alias="from")] = None,
    created_to: Annotated[datetime | None, Query(alias="to")] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, object]:
    if created_from and created_to and created_from > created_to:
        raise ValidationError(details={"fields": ["from", "to"]})
    statuses = tuple(sorted(item.value for item in status_filter or []))
    severities = tuple(sorted(item.value for item in severity or []))
    filters: dict[str, object] = {
        "status": statuses,
        "severity": severities,
        "application_id": str(application_id) if application_id else None,
        "environment_id": str(environment_id) if environment_id else None,
        "assignee_user_id": str(assignee_user_id) if assignee_user_id else None,
        "unassigned": unassigned,
        "source": source,
        "action": action,
        "category": category,
        "from": created_from.isoformat() if created_from else None,
        "to": created_to.isoformat() if created_to else None,
        "search": search,
    }
    after = _decode_cursor(cursor, organization_id, filters, crypto) if cursor else None
    items, next_key = await IncidentService(db).list_incidents(
        organization_id,
        statuses=statuses,
        severities=severities,
        application_id=application_id,
        environment_id=environment_id,
        assignee_user_id=assignee_user_id,
        unassigned=unassigned,
        source=source,
        action=action,
        category=category,
        created_from=created_from,
        created_to=created_to,
        search=search,
        after=after,
        limit=limit,
    )
    return {
        "items": items,
        "next_cursor": (
            _encode_cursor(next_key, organization_id, filters, crypto) if next_key else None
        ),
        "limit": limit,
    }


@router.get("/organizations/{organization_id}/incidents/assignees")
async def list_incident_assignees(
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return {"items": await IncidentService(db).assignees(tenant.membership)}


@router.get("/organizations/{organization_id}/incidents/{incident_id}")
async def get_incident(
    organization_id: UUID,
    incident_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return await IncidentService(db).detail(organization_id, incident_id)


@router.post("/organizations/{organization_id}/incidents", status_code=status.HTTP_201_CREATED)
async def create_incident(
    organization_id: UUID,
    body: IncidentCreateRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, object]:
    service = IncidentService(db)
    incident = await service.create_manual(
        tenant.membership,
        tenant.principal.user,
        application_id=body.application_id,
        environment_id=body.environment_id,
        title=body.title,
        severity=body.severity,
        safe_summary=body.safe_summary,
        idempotency_key=idempotency_key,
    )
    return await service.detail(organization_id, incident.incident_id)


@router.patch("/organizations/{organization_id}/incidents/{incident_id}/status")
async def update_incident_status(
    organization_id: UUID,
    incident_id: UUID,
    body: IncidentStatusRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = IncidentService(db)
    await service.transition(
        tenant.membership,
        tenant.principal.user,
        incident_id,
        body.status,
        body.version,
        body.reason,
    )
    return await service.detail(organization_id, incident_id)


@router.patch("/organizations/{organization_id}/incidents/{incident_id}/assignment")
async def update_incident_assignment(
    organization_id: UUID,
    incident_id: UUID,
    body: IncidentAssignmentRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = IncidentService(db)
    await service.assign(
        tenant.membership,
        tenant.principal.user,
        incident_id,
        body.assignee_user_id,
        body.version,
    )
    return await service.detail(organization_id, incident_id)


@router.post(
    "/organizations/{organization_id}/incidents/{incident_id}/comments",
    status_code=status.HTTP_201_CREATED,
)
async def add_incident_comment(
    organization_id: UUID,
    incident_id: UUID,
    body: IncidentCommentRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = IncidentService(db)
    comment = await service.add_comment(
        tenant.membership, tenant.principal.user, incident_id, body.body
    )
    return {
        "comment_id": str(comment.comment_id),
        "incident_id": str(comment.incident_id),
        "author_user_id": str(comment.author_user_id),
        "author_email": tenant.principal.user.email,
        "body": comment.body,
        "created_at": comment.created_at.isoformat(),
    }


def _filter_digest(filters: Mapping[str, object]) -> str:
    payload = json.dumps(filters, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()[:24]


def _encode_cursor(
    value: tuple[datetime, UUID],
    organization_id: UUID,
    filters: Mapping[str, object],
    crypto: IdentityCrypto,
) -> str:
    payload = json.dumps(
        {"at": value[0].isoformat(), "id": str(value[1]), "filters": _filter_digest(filters)},
        separators=(",", ":"),
    )
    encoded = base64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()
    signature = (
        base64.urlsafe_b64encode(crypto.verifier("incident-cursor", str(organization_id), encoded))
        .rstrip(b"=")
        .decode()
    )
    return f"{encoded}.{signature}"


def _decode_cursor(
    cursor: str,
    organization_id: UUID,
    filters: Mapping[str, object],
    crypto: IdentityCrypto,
) -> tuple[datetime, UUID]:
    try:
        encoded, signature = cursor.split(".", 1)
        expected = (
            base64.urlsafe_b64encode(
                crypto.verifier("incident-cursor", str(organization_id), encoded)
            )
            .rstrip(b"=")
            .decode()
        )
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        if payload["filters"] != _filter_digest(filters):
            raise ValueError
        return datetime.fromisoformat(payload["at"]), UUID(payload["id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValidationError(details={"fields": ["cursor"]}) from error
