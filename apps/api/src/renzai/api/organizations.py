"""Phase 5 organization, membership, and invitation HTTP endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    Principal,
    TenantPrincipal,
    csrf_principal,
    current_principal,
    get_crypto,
    get_db,
    tenant_principal,
)
from renzai.core.errors import AuthorizationError, NotFoundOrHiddenError
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.modules.memberships.domain import MembershipRole, can_manage_members
from renzai.modules.memberships.models import Membership
from renzai.modules.organizations.application import OrganizationService
from renzai.modules.organizations.models import Organization
from renzai.modules.users.models import User

router = APIRouter(tags=["organizations"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrganizationCreateRequest(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=3, max_length=63)


class OrganizationUpdateRequest(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    audit_retention_days: int | None = Field(default=None, ge=90, le=3650)


class InvitationCreateRequest(StrictModel):
    email: str = Field(min_length=3, max_length=320)
    role: MembershipRole


class MembershipUpdateRequest(StrictModel):
    role: MembershipRole


def _service(request: Request, db: AsyncSession, crypto: IdentityCrypto) -> OrganizationService:
    return OrganizationService(
        db,
        crypto,
        request.app.state.settings.identity.invitation_hours,
        request.app.state.settings.retention.audit_days,
    )


def _require_verified_if_configured(request: Request, principal: Principal) -> None:
    if (
        request.app.state.settings.identity.email_verification_required
        and principal.user.email_verified_at is None
    ):
        raise AuthorizationError(details={"reason": "email_verification_required"})


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(csrf_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    _require_verified_if_configured(request, principal)
    organization, membership = await _service(request, db, crypto).create(
        principal.user, body.name, body.slug
    )
    return _organization_view(organization, membership)


@router.get("/organizations")
async def list_organizations(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    _require_verified_if_configured(request, principal)
    rows = await _service(request, db, crypto).list_for_user(principal.user)
    return {
        "items": [_organization_view(organization, membership) for organization, membership in rows]
    }


@router.get("/organizations/{organization_id}")
async def get_organization(
    organization_id: UUID,
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    organization = await db.get(Organization, organization_id)
    if organization is None:
        raise NotFoundOrHiddenError()
    return _organization_view(organization, tenant.membership)


@router.patch("/organizations/{organization_id}")
async def update_organization(
    organization_id: UUID,
    body: OrganizationUpdateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    organization = await db.get(Organization, organization_id)
    if organization is None:
        raise NotFoundOrHiddenError()
    organization = await _service(request, db, crypto).update(
        organization,
        tenant.membership,
        tenant.principal.user,
        body.name,
        body.audit_retention_days,
    )
    return _organization_view(organization, tenant.membership)


@router.get("/organizations/{organization_id}/members")
async def list_members(
    organization_id: UUID,
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    if not can_manage_members(MembershipRole(tenant.membership.role)):
        raise AuthorizationError()
    rows = await db.execute(
        select(Membership, User)
        .join(User, User.user_id == Membership.user_id)
        .where(Membership.organization_id == organization_id, Membership.status == "active")
        .order_by(User.normalized_email)
    )
    return {
        "items": [
            {
                "membership_id": str(membership.membership_id),
                "user_id": str(user.user_id),
                "email": user.email,
                "role": membership.role,
                "status": membership.status,
            }
            for membership, user in rows
        ]
    }


@router.post("/organizations/{organization_id}/invitations", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    organization_id: UUID,
    body: InvitationCreateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    token = await _service(request, db, crypto).invite(
        organization_id, tenant.membership, tenant.principal.user, body.email, body.role
    )
    result: dict[str, object] = {"created": True}
    if request.app.state.settings.app.environment.value in {"development", "test"}:
        result["development_token"] = token
    return result


@router.post("/invitations/{token}/accept")
async def accept_invitation(
    token: Annotated[str, Path(min_length=20, max_length=256)],
    request: Request,
    principal: Annotated[Principal, Depends(csrf_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    membership = await _service(request, db, crypto).accept_invitation(token, principal.user)
    return {"membership_id": str(membership.membership_id), "role": membership.role}


@router.patch("/organizations/{organization_id}/members/{membership_id}")
async def update_member(
    organization_id: UUID,
    membership_id: UUID,
    body: MembershipUpdateRequest,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> dict[str, object]:
    membership = await _service(request, db, crypto).change_member_role(
        organization_id,
        tenant.membership,
        tenant.principal.user,
        membership_id,
        body.role,
    )
    return {"membership_id": str(membership.membership_id), "role": membership.role}


@router.delete(
    "/organizations/{organization_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    organization_id: UUID,
    membership_id: UUID,
    request: Request,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    crypto: Annotated[IdentityCrypto, Depends(get_crypto)],
) -> None:
    await _service(request, db, crypto).remove_member(
        organization_id, tenant.membership, tenant.principal.user, membership_id
    )


def _organization_view(organization: Organization, membership: Membership) -> dict[str, object]:
    return {
        "organization_id": str(organization.organization_id),
        "name": organization.name,
        "slug": organization.slug,
        "status": organization.status,
        "settings": organization.settings,
        "membership_id": str(membership.membership_id),
        "role": membership.role,
    }
