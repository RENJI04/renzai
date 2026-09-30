"""Organization, invitation, membership, and tenant-audit use cases."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.errors import AuthorizationError, ConflictError, NotFoundOrHiddenError
from renzai.core.request_context import get_request_id
from renzai.core.time import as_utc, utc_now
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.modules.audit.models import AuditEvent
from renzai.modules.memberships.domain import (
    MembershipRole,
    can_assign_role,
    can_manage_members,
    can_manage_target,
)
from renzai.modules.memberships.models import Invitation, Membership
from renzai.modules.organizations.domain import normalize_name, normalize_slug
from renzai.modules.organizations.models import Organization
from renzai.modules.users.domain import normalize_email
from renzai.modules.users.models import User


class OrganizationService:
    def __init__(
        self,
        db: AsyncSession,
        crypto: IdentityCrypto,
        invitation_hours: int,
        default_audit_retention_days: int,
    ) -> None:
        self.db = db
        self.crypto = crypto
        self.invitation_hours = invitation_hours
        self.default_audit_retention_days = default_audit_retention_days

    async def create(self, user: User, name: str, slug: str) -> tuple[Organization, Membership]:
        organization = Organization(
            name=normalize_name(name),
            slug=normalize_slug(slug),
            settings={"audit_retention_days": self.default_audit_retention_days},
        )
        self.db.add(organization)
        await self.db.flush()
        membership = Membership(
            organization_id=organization.organization_id,
            user_id=user.user_id,
            role=MembershipRole.OWNER,
            status="active",
        )
        self.db.add(membership)
        await self.db.flush()
        self._audit(
            organization.organization_id,
            user.user_id,
            "organization.created",
            "organization",
            organization.organization_id,
        )
        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise ConflictError(details={"fields": ["slug"]}) from error
        return organization, membership

    async def list_for_user(self, user: User) -> list[tuple[Organization, Membership]]:
        rows = await self.db.execute(
            select(Organization, Membership)
            .join(Membership, Membership.organization_id == Organization.organization_id)
            .where(Membership.user_id == user.user_id, Membership.status == "active")
            .order_by(Organization.name)
        )
        return list(rows.tuples())

    async def update(
        self,
        organization: Organization,
        actor: Membership,
        user: User,
        name: str | None,
        audit_retention_days: int | None,
    ) -> Organization:
        await self._lock_organization(organization.organization_id)
        current_actor = await self._actor_membership(
            organization.organization_id, actor.membership_id
        )
        if not can_manage_members(MembershipRole(current_actor.role)):
            raise AuthorizationError()
        if name is not None:
            organization.name = normalize_name(name)
        if audit_retention_days is not None:
            organization.settings = {
                **organization.settings,
                "audit_retention_days": audit_retention_days,
            }
        self._audit(
            organization.organization_id,
            user.user_id,
            "organization.updated",
            "organization",
            organization.organization_id,
        )
        await self.db.commit()
        return organization

    async def invite(
        self, organization_id: UUID, actor: Membership, user: User, email: str, role: MembershipRole
    ) -> str:
        await self._lock_organization(organization_id)
        current_actor = await self._actor_membership(organization_id, actor.membership_id)
        actor_role = MembershipRole(current_actor.role)
        if not can_manage_members(actor_role) or not can_assign_role(actor_role, role):
            raise AuthorizationError()
        target = normalize_email(email)
        now = utc_now()
        await self.db.execute(
            update(Invitation)
            .where(
                Invitation.organization_id == organization_id,
                Invitation.target_email == target,
                Invitation.role == role,
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        token = self.crypto.create_credential("invitation", "rziv_")
        invitation = Invitation(
            organization_id=organization_id,
            created_by_user_id=user.user_id,
            target_email=target,
            role=role,
            lookup=token.lookup,
            verifier=token.verifier,
            verifier_key_id=self.crypto.key_id,
            expires_at=now + timedelta(hours=self.invitation_hours),
        )
        self.db.add(invitation)
        await self.db.flush()
        self._audit(
            organization_id,
            user.user_id,
            "invitation.created",
            "invitation",
            invitation.invitation_id,
            {"role": role.value},
        )
        await self.db.commit()
        return token.public

    async def accept_invitation(self, token: str, user: User) -> Membership:
        lookup = self.crypto.lookup(token, "rziv_")
        if lookup is None:
            raise NotFoundOrHiddenError()
        invitation = (
            await self.db.execute(
                select(Invitation).where(Invitation.lookup == lookup).with_for_update()
            )
        ).scalar_one_or_none()
        now = utc_now()
        if (
            invitation is None
            or invitation.accepted_at is not None
            or invitation.revoked_at is not None
            or as_utc(invitation.expires_at) <= now
            or user.normalized_email != invitation.target_email
            or not self.crypto.parse_and_verify(
                token, "invitation", invitation.lookup, invitation.verifier, "rziv_"
            )
        ):
            raise NotFoundOrHiddenError()
        membership = (
            await self.db.execute(
                select(Membership).where(
                    Membership.organization_id == invitation.organization_id,
                    Membership.user_id == user.user_id,
                )
            )
        ).scalar_one_or_none()
        already_active = membership is not None and membership.status == "active"
        if membership is None:
            membership = Membership(
                organization_id=invitation.organization_id,
                user_id=user.user_id,
                role=invitation.role,
                status="active",
            )
            self.db.add(membership)
        elif membership.status != "active":
            membership.role = invitation.role
            membership.status = "active"
        invitation.accepted_at = now
        await self.db.flush()
        self._audit(
            invitation.organization_id,
            user.user_id,
            "invitation.accepted",
            "membership",
            membership.membership_id,
            {"role": membership.role, "already_member": already_active},
        )
        await self.db.commit()
        return membership

    async def change_member_role(
        self,
        organization_id: UUID,
        actor: Membership,
        actor_user: User,
        membership_id: UUID,
        role: MembershipRole,
    ) -> Membership:
        await self._lock_organization(organization_id)
        current_actor = await self._actor_membership(organization_id, actor.membership_id)
        target = await self._target_membership(organization_id, membership_id)
        actor_role = MembershipRole(current_actor.role)
        target_role = MembershipRole(target.role)
        if not can_manage_target(actor_role, target_role) or not can_assign_role(actor_role, role):
            raise AuthorizationError()
        if target_role is MembershipRole.OWNER and role is not MembershipRole.OWNER:
            await self._protect_last_owner(organization_id, target.membership_id)
        target.role = role
        target_user = await self.db.get(User, target.user_id)
        if target_user is not None:
            target_user.privilege_version += 1
        self._audit(
            organization_id,
            actor_user.user_id,
            "membership.role_changed",
            "membership",
            target.membership_id,
            {"from": target_role.value, "to": role.value},
        )
        await self.db.commit()
        return target

    async def remove_member(
        self,
        organization_id: UUID,
        actor: Membership,
        actor_user: User,
        membership_id: UUID,
    ) -> None:
        await self._lock_organization(organization_id)
        current_actor = await self._actor_membership(organization_id, actor.membership_id)
        target = await self._target_membership(organization_id, membership_id)
        actor_role = MembershipRole(current_actor.role)
        target_role = MembershipRole(target.role)
        if not can_manage_target(actor_role, target_role):
            raise AuthorizationError()
        if target_role is MembershipRole.OWNER:
            await self._protect_last_owner(organization_id, target.membership_id)
        target.status = "removed"
        target_user = await self.db.get(User, target.user_id)
        if target_user is not None:
            target_user.privilege_version += 1
        self._audit(
            organization_id,
            actor_user.user_id,
            "membership.removed",
            "membership",
            target.membership_id,
        )
        await self.db.commit()

    async def _target_membership(self, organization_id: UUID, membership_id: UUID) -> Membership:
        target = (
            await self.db.execute(
                select(Membership)
                .where(
                    Membership.organization_id == organization_id,
                    Membership.membership_id == membership_id,
                    Membership.status == "active",
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if target is None:
            raise NotFoundOrHiddenError()
        return target

    async def _actor_membership(self, organization_id: UUID, membership_id: UUID) -> Membership:
        actor = (
            await self.db.execute(
                select(Membership)
                .where(
                    Membership.organization_id == organization_id,
                    Membership.membership_id == membership_id,
                    Membership.status == "active",
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if actor is None:
            raise AuthorizationError()
        return actor

    async def _lock_organization(self, organization_id: UUID) -> None:
        if self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            lock_key = int.from_bytes(organization_id.bytes[:8], "big", signed=True)
            await self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})

    async def _protect_last_owner(self, organization_id: UUID, target_id: UUID) -> None:
        owners = list(
            (
                await self.db.execute(
                    select(Membership)
                    .where(
                        Membership.organization_id == organization_id,
                        Membership.status == "active",
                        Membership.role == MembershipRole.OWNER,
                    )
                    .with_for_update()
                )
            ).scalars()
        )
        if len(owners) <= 1 and any(owner.membership_id == target_id for owner in owners):
            raise ConflictError(details={"reason": "last_owner"})

    def _audit(
        self,
        organization_id: UUID,
        actor_user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: object,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.db.add(
            AuditEvent(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                outcome="success",
                request_id=get_request_id(),
                safe_metadata=metadata or {},
            )
        )
