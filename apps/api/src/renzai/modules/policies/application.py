"""Tenant-safe policy management, versioning, bootstrap, and evaluation snapshots."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundOrHiddenError,
    ValidationError,
)
from renzai.core.ids import new_uuid7
from renzai.core.request_context import get_request_id
from renzai.core.time import utc_now
from renzai.modules.applications.models import Application
from renzai.modules.audit.models import AuditEvent
from renzai.modules.environments.models import Environment
from renzai.modules.memberships.domain import MembershipRole
from renzai.modules.memberships.models import Membership
from renzai.modules.policies.baseline import BASELINE_POLICIES
from renzai.modules.policies.domain import (
    PolicyAction,
    PolicyEvaluationError,
    PolicySnapshot,
    PolicyValidationError,
)
from renzai.modules.policies.domain import PolicyCondition as DomainCondition
from renzai.modules.policies.models import Policy, PolicyCondition, PolicyVersion
from renzai.modules.risk.application import ensure_system_risk_profile
from renzai.modules.users.models import User

POLICY_EDITORS = {
    MembershipRole.OWNER,
    MembershipRole.ADMIN,
    MembershipRole.SECURITY_ANALYST,
}
RATIONALE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,95}$")


@dataclass(frozen=True, slots=True)
class PolicyBundle:
    policy: Policy
    version: PolicyVersion
    conditions: tuple[DomainCondition, ...]
    latest_version: int


async def bootstrap_application_baseline(
    db: AsyncSession,
    application: Application,
    *,
    actor_user_id: UUID | None = None,
) -> int:
    """Add the reviewed application baseline exactly once without committing."""
    await ensure_system_risk_profile(db)
    existing = set(
        (
            await db.execute(
                select(Policy.baseline_key).where(
                    Policy.application_id == application.application_id,
                    Policy.baseline_key.is_not(None),
                )
            )
        ).scalars()
    )
    created = 0
    for definition in BASELINE_POLICIES:
        if definition.key in existing:
            continue
        policy = Policy(
            policy_id=new_uuid7(),
            organization_id=application.organization_id,
            application_id=application.application_id,
            environment_id=None,
            scope_kind="application",
            scope_id=application.application_id,
            name=definition.name,
            phase=definition.phase,
            priority=definition.priority,
            enabled=True,
            active_version=1,
            status="active",
            is_baseline=True,
            baseline_key=definition.key,
        )
        version = PolicyVersion(
            policy_version_id=new_uuid7(),
            policy_id=policy.policy_id,
            organization_id=application.organization_id,
            version=1,
            action=definition.action.value,
            rationale_code=definition.rationale_code,
            condition_mode="all",
            redaction_targets=list(definition.redaction_targets),
            activated_at=utc_now(),
        )
        db.add(policy)
        await db.flush()
        db.add(version)
        await db.flush()
        for ordinal, condition in enumerate(definition.conditions):
            db.add(
                PolicyCondition(
                    policy_version_id=version.policy_version_id,
                    ordinal=ordinal,
                    field=condition.field,
                    operator=condition.operator,
                    value=condition.value,
                )
            )
        created += 1
    if created and actor_user_id is not None:
        db.add(
            AuditEvent(
                organization_id=application.organization_id,
                actor_user_id=actor_user_id,
                action="policy.baseline_bootstrapped",
                resource_type="application",
                resource_id=str(application.application_id),
                outcome="success",
                request_id=get_request_id(),
                safe_metadata={"baseline": "renzai-v1", "policy_count": created},
            )
        )
    await db.flush()
    return created


class PolicyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        actor: Membership,
        user: User,
        *,
        name: str,
        scope_kind: str,
        scope_id: UUID,
        phase: str,
        priority: int,
        enabled: bool,
        action: PolicyAction,
        rationale_code: str,
        condition_mode: str,
        conditions: tuple[DomainCondition, ...],
        redaction_targets: tuple[str, ...],
    ) -> PolicyBundle:
        self.require_editor(actor)
        application_id, environment_id = await self._resolve_scope(
            actor.organization_id, scope_kind, scope_id
        )
        self._validate_version(
            scope_kind,
            scope_id,
            phase,
            priority,
            action,
            rationale_code,
            condition_mode,
            conditions,
            redaction_targets,
        )
        policy = Policy(
            policy_id=new_uuid7(),
            organization_id=actor.organization_id,
            application_id=application_id,
            environment_id=environment_id,
            scope_kind=scope_kind,
            scope_id=scope_id,
            name=self._name(name),
            phase=phase,
            priority=priority,
            enabled=enabled,
            active_version=1,
            status="active",
            is_baseline=False,
        )
        self.db.add(policy)
        version = self._add_version(
            policy,
            1,
            action,
            rationale_code,
            condition_mode,
            conditions,
            redaction_targets,
            activated=True,
        )
        self._audit(actor, user, "policy.created", policy, {"version": 1})
        await self._commit_conflict()
        return PolicyBundle(policy, version, conditions, 1)

    async def list_policies(self, organization_id: UUID) -> list[PolicyBundle]:
        policies = list(
            (
                await self.db.execute(
                    select(Policy)
                    .where(Policy.organization_id == organization_id)
                    .order_by(Policy.created_at.desc(), Policy.policy_id.desc())
                )
            ).scalars()
        )
        return [await self.bundle(policy) for policy in policies]

    async def get(self, organization_id: UUID, policy_id: UUID) -> Policy:
        policy = (
            await self.db.execute(
                select(Policy).where(
                    Policy.organization_id == organization_id,
                    Policy.policy_id == policy_id,
                )
            )
        ).scalar_one_or_none()
        if policy is None:
            raise NotFoundOrHiddenError()
        return policy

    async def bundle(self, policy: Policy, version_number: int | None = None) -> PolicyBundle:
        selected_version = version_number or policy.active_version
        version = (
            await self.db.execute(
                select(PolicyVersion).where(
                    PolicyVersion.policy_id == policy.policy_id,
                    PolicyVersion.version == selected_version,
                )
            )
        ).scalar_one_or_none()
        if version is None:
            raise NotFoundOrHiddenError()
        conditions = await self._conditions(version.policy_version_id)
        latest = int(
            await self.db.scalar(
                select(func.max(PolicyVersion.version)).where(
                    PolicyVersion.policy_id == policy.policy_id
                )
            )
            or version.version
        )
        return PolicyBundle(policy, version, conditions, latest)

    async def versions(self, policy: Policy) -> list[PolicyBundle]:
        rows = list(
            (
                await self.db.execute(
                    select(PolicyVersion)
                    .where(PolicyVersion.policy_id == policy.policy_id)
                    .order_by(PolicyVersion.version.desc())
                )
            ).scalars()
        )
        latest = rows[0].version if rows else policy.active_version
        return [
            PolicyBundle(policy, row, await self._conditions(row.policy_version_id), latest)
            for row in rows
        ]

    async def create_version(
        self,
        actor: Membership,
        user: User,
        policy: Policy,
        *,
        expected_version: int,
        name: str | None,
        priority: int | None,
        action: PolicyAction,
        rationale_code: str,
        condition_mode: str,
        conditions: tuple[DomainCondition, ...],
        redaction_targets: tuple[str, ...],
    ) -> PolicyBundle:
        self.require_editor(actor)
        if policy.status == "archived" or policy.active_version != expected_version:
            raise ConflictError(details={"reason": "stale_or_archived_policy"})
        target_priority = priority if priority is not None else policy.priority
        self._validate_version(
            policy.scope_kind,
            policy.scope_id,
            policy.phase,
            target_priority,
            action,
            rationale_code,
            condition_mode,
            conditions,
            redaction_targets,
        )
        latest = int(
            await self.db.scalar(
                select(func.max(PolicyVersion.version)).where(
                    PolicyVersion.policy_id == policy.policy_id
                )
            )
            or 0
        )
        new_number = latest + 1
        if name is not None:
            policy.name = self._name(name)
        policy.priority = target_priority
        version = self._add_version(
            policy,
            new_number,
            action,
            rationale_code,
            condition_mode,
            conditions,
            redaction_targets,
            activated=False,
        )
        self._audit(
            actor,
            user,
            "policy.version_created",
            policy,
            {"version": new_number},
        )
        await self._commit_conflict()
        return PolicyBundle(policy, version, conditions, new_number)

    async def set_enabled(
        self,
        actor: Membership,
        user: User,
        policy: Policy,
        *,
        enabled: bool,
        expected_version: int,
        version: int | None = None,
    ) -> PolicyBundle:
        self.require_editor(actor)
        self._check_mutable(policy, expected_version)
        if version is not None:
            await self._select_version(policy, version)
        policy.enabled = enabled
        self._audit(
            actor,
            user,
            "policy.enabled" if enabled else "policy.disabled",
            policy,
            {"version": policy.active_version},
        )
        await self._commit_conflict()
        return await self.bundle(policy)

    async def activate(
        self,
        actor: Membership,
        user: User,
        policy: Policy,
        *,
        version: int,
        expected_version: int,
        rollback: bool = False,
    ) -> PolicyBundle:
        self.require_editor(actor)
        self._check_mutable(policy, expected_version)
        if rollback and version >= policy.active_version:
            raise ConflictError(details={"reason": "rollback_requires_older_version"})
        await self._select_version(policy, version)
        self._audit(
            actor,
            user,
            "policy.rolled_back" if rollback else "policy.activated",
            policy,
            {"version": version},
        )
        await self._commit_conflict()
        return await self.bundle(policy)

    async def archive(
        self, actor: Membership, user: User, policy: Policy, expected_version: int
    ) -> PolicyBundle:
        self.require_editor(actor)
        self._check_mutable(policy, expected_version)
        policy.enabled = False
        policy.status = "archived"
        policy.archived_at = utc_now()
        self._audit(actor, user, "policy.archived", policy)
        await self.db.commit()
        return await self.bundle(policy)

    async def active_snapshots(
        self,
        organization_id: UUID,
        application_id: UUID,
        environment_id: UUID,
        phase: str,
    ) -> tuple[PolicySnapshot, ...]:
        rows = (
            await self.db.execute(
                select(Policy, PolicyVersion)
                .join(
                    PolicyVersion,
                    (PolicyVersion.policy_id == Policy.policy_id)
                    & (PolicyVersion.version == Policy.active_version),
                )
                .where(
                    Policy.organization_id == organization_id,
                    Policy.phase == phase,
                    Policy.enabled.is_(True),
                    Policy.status == "active",
                    (
                        (Policy.scope_kind == "organization")
                        | (
                            (Policy.scope_kind == "application")
                            & (Policy.scope_id == application_id)
                        )
                        | (
                            (Policy.scope_kind == "environment")
                            & (Policy.scope_id == environment_id)
                        )
                    ),
                )
                .order_by(Policy.scope_kind, Policy.priority)
            )
        ).all()
        snapshots: list[PolicySnapshot] = []
        for policy, version in rows:
            try:
                snapshots.append(
                    PolicySnapshot(
                        policy_id=str(policy.policy_id),
                        version_id=str(version.policy_version_id),
                        version=version.version,
                        scope_kind=policy.scope_kind,
                        scope_id=str(policy.scope_id),
                        phase=policy.phase,
                        priority=policy.priority,
                        enabled=policy.enabled,
                        action=PolicyAction(version.action),
                        rationale_code=version.rationale_code,
                        condition_mode=version.condition_mode,
                        conditions=await self._conditions(version.policy_version_id),
                        redaction_targets=tuple(version.redaction_targets),
                    )
                )
            except (ValueError, TypeError) as error:
                raise PolicyEvaluationError("active policy snapshot is invalid") from error
        return tuple(snapshots)

    async def require_analysis_scope(
        self, organization_id: UUID, application_id: UUID, environment_id: UUID
    ) -> None:
        scope = (
            await self.db.execute(
                select(Environment.environment_id)
                .join(
                    Application,
                    (Application.application_id == Environment.application_id)
                    & (Application.organization_id == Environment.organization_id),
                )
                .where(
                    Environment.organization_id == organization_id,
                    Environment.application_id == application_id,
                    Environment.environment_id == environment_id,
                )
            )
        ).scalar_one_or_none()
        if scope is None:
            raise NotFoundOrHiddenError()

    async def _resolve_scope(
        self, organization_id: UUID, scope_kind: str, scope_id: UUID
    ) -> tuple[UUID | None, UUID | None]:
        if scope_kind == "organization":
            if scope_id != organization_id:
                raise NotFoundOrHiddenError()
            return None, None
        if scope_kind == "application":
            application = (
                await self.db.execute(
                    select(Application).where(
                        Application.organization_id == organization_id,
                        Application.application_id == scope_id,
                    )
                )
            ).scalar_one_or_none()
            if application is None:
                raise NotFoundOrHiddenError()
            return application.application_id, None
        if scope_kind == "environment":
            environment = (
                await self.db.execute(
                    select(Environment).where(
                        Environment.organization_id == organization_id,
                        Environment.environment_id == scope_id,
                    )
                )
            ).scalar_one_or_none()
            if environment is None:
                raise NotFoundOrHiddenError()
            return environment.application_id, environment.environment_id
        raise ConflictError(details={"fields": ["scope_kind"]})

    def _add_version(
        self,
        policy: Policy,
        version_number: int,
        action: PolicyAction,
        rationale_code: str,
        condition_mode: str,
        conditions: tuple[DomainCondition, ...],
        redaction_targets: tuple[str, ...],
        *,
        activated: bool,
    ) -> PolicyVersion:
        version = PolicyVersion(
            policy_version_id=new_uuid7(),
            policy_id=policy.policy_id,
            organization_id=policy.organization_id,
            version=version_number,
            action=action.value,
            rationale_code=rationale_code,
            condition_mode=condition_mode,
            redaction_targets=list(redaction_targets),
            activated_at=utc_now() if activated else None,
        )
        self.db.add(version)
        for ordinal, condition in enumerate(conditions):
            self.db.add(
                PolicyCondition(
                    policy_version_id=version.policy_version_id,
                    ordinal=ordinal,
                    field=condition.field,
                    operator=condition.operator,
                    value=condition.value,
                )
            )
        return version

    async def _conditions(self, version_id: UUID) -> tuple[DomainCondition, ...]:
        rows = list(
            (
                await self.db.execute(
                    select(PolicyCondition)
                    .where(PolicyCondition.policy_version_id == version_id)
                    .order_by(PolicyCondition.ordinal)
                )
            ).scalars()
        )
        return tuple(DomainCondition(row.field, row.operator, row.value) for row in rows)

    async def _select_version(self, policy: Policy, version_number: int) -> None:
        version = (
            await self.db.execute(
                select(PolicyVersion).where(
                    PolicyVersion.policy_id == policy.policy_id,
                    PolicyVersion.version == version_number,
                )
            )
        ).scalar_one_or_none()
        if version is None:
            raise NotFoundOrHiddenError()
        policy.active_version = version_number
        if version.activated_at is None:
            version.activated_at = utc_now()

    @staticmethod
    def _check_mutable(policy: Policy, expected_version: int) -> None:
        if policy.status == "archived" or policy.active_version != expected_version:
            raise ConflictError(details={"reason": "stale_or_archived_policy"})

    @staticmethod
    def require_editor(actor: Membership) -> None:
        if MembershipRole(actor.role) not in POLICY_EDITORS:
            raise AuthorizationError()

    @staticmethod
    def _validate_version(
        scope_kind: str,
        scope_id: UUID,
        phase: str,
        priority: int,
        action: PolicyAction,
        rationale_code: str,
        condition_mode: str,
        conditions: tuple[DomainCondition, ...],
        redaction_targets: tuple[str, ...],
    ) -> None:
        if not RATIONALE_CODE.fullmatch(rationale_code):
            raise ConflictError(details={"fields": ["rationale_code"]})
        try:
            PolicySnapshot(
                policy_id="validation",
                version_id="validation",
                version=1,
                scope_kind=scope_kind,
                scope_id=str(scope_id),
                phase=phase,
                priority=priority,
                enabled=True,
                action=action,
                rationale_code=rationale_code,
                condition_mode=condition_mode,
                conditions=conditions,
                redaction_targets=redaction_targets,
            )
        except PolicyValidationError as error:
            raise ValidationError(details={"fields": ["policy"]}) from error

    @staticmethod
    def _name(value: str) -> str:
        return " ".join(value.strip().split())

    async def _commit_conflict(self) -> None:
        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise ConflictError(details={"fields": ["priority"]}) from error

    def _audit(
        self,
        actor: Membership,
        user: User,
        action: str,
        policy: Policy,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.db.add(
            AuditEvent(
                organization_id=actor.organization_id,
                actor_user_id=user.user_id,
                action=action,
                resource_type="policy",
                resource_id=str(policy.policy_id),
                outcome="success",
                request_id=get_request_id(),
                safe_metadata=metadata or {},
            )
        )
