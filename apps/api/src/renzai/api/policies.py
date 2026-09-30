"""Risk-profile inspection and tenant-scoped policy management APIs."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.api.dependencies import (
    Principal,
    TenantPrincipal,
    csrf_principal,
    get_db,
    tenant_principal,
)
from renzai.core.errors import ValidationError
from renzai.modules.policies.application import PolicyBundle, PolicyService
from renzai.modules.policies.domain import (
    PolicyAction,
    PolicyCondition,
    PolicyFacts,
    PolicyValidationError,
    evaluate_policies,
)
from renzai.modules.risk.application import ensure_system_risk_profile
from renzai.modules.risk.domain import confidence_band

router = APIRouter(tags=["policies"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConditionRequest(StrictModel):
    field: str = Field(min_length=1, max_length=48)
    operator: str = Field(min_length=1, max_length=32)
    value: Any


class PolicyCreateRequest(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    scope_kind: Literal["organization", "application", "environment"]
    scope_id: UUID
    phase: Literal["input", "output"]
    priority: int = Field(ge=1, le=1_000_000)
    enabled: bool = False
    action: PolicyAction
    rationale_code: str = Field(min_length=1, max_length=96)
    condition_mode: Literal["all", "any"]
    conditions: list[ConditionRequest] = Field(min_length=1, max_length=20)
    redaction_targets: list[str] = Field(default_factory=list, max_length=11)


class PolicyVersionRequest(StrictModel):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    priority: int | None = Field(default=None, ge=1, le=1_000_000)
    action: PolicyAction
    rationale_code: str = Field(min_length=1, max_length=96)
    condition_mode: Literal["all", "any"]
    conditions: list[ConditionRequest] = Field(min_length=1, max_length=20)
    redaction_targets: list[str] = Field(default_factory=list, max_length=11)


class PolicyStateRequest(StrictModel):
    expected_version: int = Field(ge=1)
    version: int | None = Field(default=None, ge=1)


class PolicyVersionSelectRequest(StrictModel):
    expected_version: int = Field(ge=1)
    version: int = Field(ge=1)


class PolicyPreviewRequest(StrictModel):
    application_id: UUID
    environment_id: UUID
    phase: Literal["input", "output"]
    categories: list[str] = Field(default_factory=list, max_length=32)
    detector_ids: list[str] = Field(default_factory=list, max_length=64)
    risk_score: int = Field(ge=0, le=100)
    severity: Literal["low", "medium", "high", "critical"]
    confidence: int = Field(ge=0, le=100)
    environment_type: Literal["development", "staging", "production"]
    source: Literal["analyze", "playground"]


def _conditions(rows: list[ConditionRequest]) -> tuple[PolicyCondition, ...]:
    try:
        return tuple(PolicyCondition(row.field, row.operator, row.value) for row in rows)
    except PolicyValidationError as error:
        raise ValidationError(details={"fields": ["conditions"]}) from error


@router.get("/organizations/{organization_id}/risk-profile")
async def get_risk_profile(
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    profile = await ensure_system_risk_profile(db)
    return {
        "risk_profile_id": profile.profile_id,
        "name": profile.name,
        "active_version": profile.version,
        "formula_version": profile.formula_version,
        "weights": {category.value: weight for category, weight in profile.weights.items()},
        "thresholds": {"low": 0, "medium": 25, "high": 50, "critical": 75},
        "system_owned": True,
    }


@router.post("/organizations/{organization_id}/policies", status_code=status.HTTP_201_CREATED)
async def create_policy(
    organization_id: UUID,
    body: PolicyCreateRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    bundle = await PolicyService(db).create(
        tenant.membership,
        tenant.principal.user,
        name=body.name,
        scope_kind=body.scope_kind,
        scope_id=body.scope_id,
        phase=body.phase,
        priority=body.priority,
        enabled=body.enabled,
        action=body.action,
        rationale_code=body.rationale_code,
        condition_mode=body.condition_mode,
        conditions=_conditions(body.conditions),
        redaction_targets=tuple(body.redaction_targets),
    )
    return _view(bundle)


@router.get("/organizations/{organization_id}/policies")
async def list_policies(
    organization_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    return {
        "items": [_view(item) for item in await PolicyService(db).list_policies(organization_id)]
    }


@router.get("/organizations/{organization_id}/policies/{policy_id}")
async def get_policy(
    organization_id: UUID,
    policy_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    version: Annotated[int | None, Query(ge=1)] = None,
) -> dict[str, object]:
    service = PolicyService(db)
    policy = await service.get(organization_id, policy_id)
    return _view(await service.bundle(policy, version))


@router.patch("/organizations/{organization_id}/policies/{policy_id}")
async def create_policy_version(
    organization_id: UUID,
    policy_id: UUID,
    body: PolicyVersionRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = PolicyService(db)
    policy = await service.get(organization_id, policy_id)
    bundle = await service.create_version(
        tenant.membership,
        tenant.principal.user,
        policy,
        expected_version=body.expected_version,
        name=body.name,
        priority=body.priority,
        action=body.action,
        rationale_code=body.rationale_code,
        condition_mode=body.condition_mode,
        conditions=_conditions(body.conditions),
        redaction_targets=tuple(body.redaction_targets),
    )
    return _view(bundle)


@router.get("/organizations/{organization_id}/policies/{policy_id}/versions")
async def list_policy_versions(
    organization_id: UUID,
    policy_id: UUID,
    _: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = PolicyService(db)
    policy = await service.get(organization_id, policy_id)
    return {"items": [_view(item) for item in await service.versions(policy)]}


@router.post("/organizations/{organization_id}/policies/{policy_id}/enable")
async def enable_policy(
    organization_id: UUID,
    policy_id: UUID,
    body: PolicyStateRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = PolicyService(db)
    policy = await service.get(organization_id, policy_id)
    return _view(
        await service.set_enabled(
            tenant.membership,
            tenant.principal.user,
            policy,
            enabled=True,
            expected_version=body.expected_version,
            version=body.version,
        )
    )


@router.post("/organizations/{organization_id}/policies/{policy_id}/disable")
async def disable_policy(
    organization_id: UUID,
    policy_id: UUID,
    body: PolicyStateRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = PolicyService(db)
    policy = await service.get(organization_id, policy_id)
    return _view(
        await service.set_enabled(
            tenant.membership,
            tenant.principal.user,
            policy,
            enabled=False,
            expected_version=body.expected_version,
        )
    )


@router.post("/organizations/{organization_id}/policies/{policy_id}/activate")
async def activate_policy_version(
    organization_id: UUID,
    policy_id: UUID,
    body: PolicyVersionSelectRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = PolicyService(db)
    policy = await service.get(organization_id, policy_id)
    return _view(
        await service.activate(
            tenant.membership,
            tenant.principal.user,
            policy,
            version=body.version,
            expected_version=body.expected_version,
        )
    )


@router.post("/organizations/{organization_id}/policies/{policy_id}/rollback")
async def rollback_policy_version(
    organization_id: UUID,
    policy_id: UUID,
    body: PolicyVersionSelectRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = PolicyService(db)
    policy = await service.get(organization_id, policy_id)
    return _view(
        await service.activate(
            tenant.membership,
            tenant.principal.user,
            policy,
            version=body.version,
            expected_version=body.expected_version,
            rollback=True,
        )
    )


@router.post("/organizations/{organization_id}/policies/{policy_id}/archive")
async def archive_policy(
    organization_id: UUID,
    policy_id: UUID,
    body: PolicyStateRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = PolicyService(db)
    policy = await service.get(organization_id, policy_id)
    return _view(
        await service.archive(
            tenant.membership, tenant.principal.user, policy, body.expected_version
        )
    )


@router.post("/organizations/{organization_id}/policies/preview")
async def preview_policies(
    organization_id: UUID,
    body: PolicyPreviewRequest,
    _: Annotated[Principal, Depends(csrf_principal)],
    tenant: Annotated[TenantPrincipal, Depends(tenant_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    service = PolicyService(db)
    service.require_editor(tenant.membership)
    await service.require_analysis_scope(organization_id, body.application_id, body.environment_id)
    snapshots = await service.active_snapshots(
        organization_id, body.application_id, body.environment_id, body.phase
    )
    decision = evaluate_policies(
        snapshots,
        PolicyFacts(
            phase=body.phase,
            categories=frozenset(body.categories),
            detector_ids=frozenset(body.detector_ids),
            risk_score=body.risk_score,
            severity=body.severity,
            confidence_band=confidence_band(body.confidence).value,
            application_id=str(body.application_id),
            environment_type=body.environment_type,
            source=body.source,
            organization_id=str(organization_id),
            environment_id=str(body.environment_id),
        ),
    )
    return {
        "action": decision.action.value,
        "policy_match": decision.selected_policy_id,
        "scope_winners": [winner.as_dict() for winner in decision.scope_winners],
        "evaluated_policy_versions": list(decision.evaluated_policy_versions),
        "rationale_code": decision.rationale_code,
    }


def _view(bundle: PolicyBundle) -> dict[str, object]:
    policy = bundle.policy
    version = bundle.version
    return {
        "policy_id": str(policy.policy_id),
        "organization_id": str(policy.organization_id),
        "name": policy.name,
        "scope_kind": policy.scope_kind,
        "scope_id": str(policy.scope_id),
        "phase": policy.phase,
        "priority": policy.priority,
        "enabled": policy.enabled,
        "status": policy.status,
        "is_baseline": policy.is_baseline,
        "baseline_key": policy.baseline_key,
        "active_version": policy.active_version,
        "latest_version": bundle.latest_version,
        "version": {
            "policy_version_id": str(version.policy_version_id),
            "version": version.version,
            "action": version.action,
            "rationale_code": version.rationale_code,
            "condition_mode": version.condition_mode,
            "conditions": [condition.as_dict() for condition in bundle.conditions],
            "redaction_targets": version.redaction_targets,
            "created_at": version.created_at.isoformat(),
            "activated_at": version.activated_at.isoformat() if version.activated_at else None,
        },
        "created_at": policy.created_at.isoformat(),
        "updated_at": policy.updated_at.isoformat(),
        "archived_at": policy.archived_at.isoformat() if policy.archived_at else None,
    }
