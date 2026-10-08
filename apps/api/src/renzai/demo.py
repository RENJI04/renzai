"""Opt-in, synthetic Phase 16 demonstration data.

This module is not imported by the application runtime.  The wrappers in ``scripts/``
call it explicitly after an operator has registered a synthetic ``@demo.invalid`` user.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.db import models as _models  # noqa: F401 - registers every table with metadata
from renzai.db.base import Base
from renzai.modules.ai_intelligence.models import (
    AIIntelligenceConfiguration,
    AIIntelligenceRequest,
    AIIntelligenceResult,
)
from renzai.modules.applications.models import Application
from renzai.modules.environments.models import Environment
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.incidents.models import (
    Incident,
    IncidentComment,
    IncidentSecurityEvent,
    IncidentTimelineEvent,
)
from renzai.modules.memberships.models import Membership
from renzai.modules.organizations.models import Organization
from renzai.modules.policies.application import bootstrap_application_baseline
from renzai.modules.policies.models import (
    Policy,
    PolicyCondition,
    PolicyDecision,
    PolicyVersion,
)
from renzai.modules.providers.models import ProviderConfiguration
from renzai.modules.risk.domain import SYSTEM_RISK_PROFILE_ID, SYSTEM_RISK_PROFILE_VERSION_ID
from renzai.modules.risk.models import RiskContribution
from renzai.modules.security.domain.types import Category
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent
from renzai.modules.users.models import User

DEMO_ORGANIZATION_NAME = "Renzai Demo Lab"
DEMO_ORGANIZATION_SLUG = "renzai-demo-lab"
DEMO_MARKER = "renzai-phase-16-v1"
DEMO_NAMESPACE = UUID("f0c540ce-c26d-5ad7-b431-d5cb9508e7ad")
DEMO_OWNER_DOMAIN = "@demo.invalid"
APPLICATION_NAMES = ("Support Copilot", "Finance Assistant", "Developer Assistant")
ENVIRONMENT_TYPES = ("development", "staging", "production")


class DemoSafetyError(RuntimeError):
    """The requested demo operation did not satisfy the bounded safety rules."""


@dataclass(frozen=True, slots=True)
class DemoSummary:
    organization_id: UUID
    applications: int
    environments: int
    analyses: int
    incidents: int
    provider_calls: int
    ai_results: int
    already_present: bool = False


def demo_id(label: str) -> UUID:
    return uuid5(DEMO_NAMESPACE, label)


def _normalize_demo_email(value: str) -> str:
    email = value.strip().casefold()
    if not email.endswith(DEMO_OWNER_DOMAIN) or len(email) <= len(DEMO_OWNER_DOMAIN):
        raise DemoSafetyError("demo owner must use the reserved @demo.invalid domain")
    return email


async def seed_demo(
    db: AsyncSession, *, owner_email: str = "analyst@demo.invalid", now: datetime | None = None
) -> DemoSummary:
    """Create the deterministic demo tenant without creating any credential."""

    normalized_email = _normalize_demo_email(owner_email)
    owner = await db.scalar(select(User).where(User.normalized_email == normalized_email))
    if owner is None or owner.status != "active":
        raise DemoSafetyError(
            "register the active synthetic demo owner before seeding; no password is created here"
        )

    existing = await db.scalar(
        select(Organization).where(Organization.slug == DEMO_ORGANIZATION_SLUG)
    )
    if existing is not None:
        _require_demo_organization(existing)
        return await _summary(db, existing.organization_id, already_present=True)

    seeded_at = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    organization_id = demo_id("organization")
    organization = Organization(
        organization_id=organization_id,
        name=DEMO_ORGANIZATION_NAME,
        slug=DEMO_ORGANIZATION_SLUG,
        status="active",
        settings={
            "audit_retention_days": 365,
            "demo_dataset": DEMO_MARKER,
            "demo_content": "synthetic-only",
        },
        created_at=seeded_at,
        updated_at=seeded_at,
    )
    db.add(organization)
    await db.flush()
    db.add(
        Membership(
            membership_id=demo_id("membership:owner"),
            organization_id=organization_id,
            user_id=owner.user_id,
            role="owner",
            status="active",
            joined_at=seeded_at,
            updated_at=seeded_at,
        )
    )
    await db.flush()

    applications: list[Application] = []
    environments: dict[tuple[str, str], Environment] = {}
    for application_name in APPLICATION_NAMES:
        app_key = application_name.casefold().replace(" ", "-")
        application = Application(
            application_id=demo_id(f"application:{app_key}"),
            organization_id=organization_id,
            name=application_name,
            name_key=application_name.casefold(),
            status="active",
            privacy_mode="METADATA_ONLY",
            safe_content_persistence=False,
            security_retention_days=30,
            created_at=seeded_at,
            updated_at=seeded_at,
        )
        db.add(application)
        applications.append(application)
        await db.flush()
        await bootstrap_application_baseline(db, application, actor_user_id=owner.user_id)
        for environment_type in ENVIRONMENT_TYPES:
            environment = Environment(
                environment_id=demo_id(f"environment:{app_key}:{environment_type}"),
                application_id=application.application_id,
                organization_id=organization_id,
                type=environment_type,
                status="active",
                created_at=seeded_at,
                updated_at=seeded_at,
            )
            db.add(environment)
            environments[(application_name, environment_type)] = environment
    await db.flush()

    providers: dict[tuple[str, str], ProviderConfiguration] = {}
    for application in applications:
        for environment_type in ENVIRONMENT_TYPES:
            environment = environments[(application.name, environment_type)]
            provider = ProviderConfiguration(
                provider_id=demo_id(f"provider:{application.name.casefold()}:{environment_type}"),
                organization_id=organization_id,
                application_id=application.application_id,
                environment_id=environment.environment_id,
                kind="openai_compatible_remote",
                name=f"{application.name} {environment_type} synthetic provider",
                name_key=(f"{application.name.casefold()} {environment_type} synthetic provider"),
                base_url="https://provider.demo.invalid/v1",
                model="synthetic-demo-model",
                credential_ciphertext=None,
                credential_key_id=None,
                supports_seed=True,
                max_tokens=512,
                connect_timeout_seconds=3,
                chat_timeout_seconds=30,
                health_timeout_seconds=5,
                response_max_bytes=64 * 1024,
                status="disabled",
                validation_policy_version="1.0.0",
                last_validation_status="never",
                last_validated_at=None,
                created_at=seeded_at,
                updated_at=seeded_at,
            )
            db.add(provider)
            providers[(application.name, environment_type)] = provider
    await db.flush()

    categories = tuple(Category)
    statuses = ("open", "investigating", "resolved", "ignored", "false_positive")
    analyses: list[AnalysisResult] = []
    incidents: list[Incident] = []
    for index in range(28):
        category = categories[index % len(categories)] if index < 22 else None
        application = applications[index % len(applications)]
        environment_type = ENVIRONMENT_TYPES[index % len(ENVIRONMENT_TYPES)]
        environment = environments[(application.name, environment_type)]
        is_incident = index < 8
        if is_incident:
            action = "block" if index % 2 == 0 else "require_review"
            score = 88 if action == "block" else 63
        elif category is Category.SECRET_EXPOSURE:
            action, score = "redact", 80
        elif category is None:
            action, score = "allow", 0
        elif index % 4 == 0:
            action, score = "flag", 38
        else:
            action, score = "allow", 18
        severity = _severity(score)
        occurred_at = seeded_at - timedelta(hours=index * 5)
        event_id = demo_id(f"event:{index}")
        analysis_id = demo_id(f"analysis:{index}")
        source = (
            "gateway"
            if is_incident or index % 3 == 0
            else ("playground" if index % 3 == 1 else "analyze")
        )
        event = SecurityEvent(
            event_id=event_id,
            organization_id=organization_id,
            application_id=application.application_id,
            environment_id=environment.environment_id,
            direction="output" if category is Category.SECRET_EXPOSURE else "input",
            source=source,
            occurred_at=occurred_at,
            correlation_id=f"demo-{index:03d}",
            privacy_mode="METADATA_ONLY",
            content=None,
            content_bytes=64 + index,
            retention_days=30,
            action=action,
            risk_score=score,
            risk_severity=severity,
            risk_profile_id=UUID(SYSTEM_RISK_PROFILE_ID),
            risk_profile_version=1,
        )
        analysis = AnalysisResult(
            analysis_id=analysis_id,
            event_id=event_id,
            completed_at=occurred_at + timedelta(milliseconds=12),
            normalization_version="1.0.0",
            ruleset_version="1.0.0",
            status="completed",
            finding_count=1 if category is not None else 0,
            normalization_ms=1,
            detector_ms=4,
            total_ms=12,
            capabilities={"demo": True, "content_persisted": False},
            risk_profile_id=UUID(SYSTEM_RISK_PROFILE_ID),
            risk_profile_version_id=UUID(SYSTEM_RISK_PROFILE_VERSION_ID),
            risk_profile_version=1,
            risk_score=score,
            risk_severity=severity,
            risk_confidence=92 if category is not None else 100,
            base_score=score,
            corroboration_bonus=0,
            critical_floor=80 if category is Category.SECRET_EXPOSURE else 0,
            action=action,
            risk_ms=2,
            policy_ms=2,
        )
        db.add(event)
        await db.flush()
        db.add(analysis)
        await db.flush()
        analyses.append(analysis)
        if category is not None:
            detector_id = _detector_id(category)
            db.add(
                Finding(
                    finding_id=demo_id(f"finding:{index}"),
                    analysis_id=analysis_id,
                    detector_id=detector_id,
                    detector_version="1.0.0",
                    ruleset_version="1.0.0",
                    category=category.value,
                    direction=event.direction,
                    severity=severity,
                    confidence=92,
                    evidence={"kind": "classification_only", "label": "synthetic_demo"},
                    safe_explanation="Synthetic demonstration finding generated for the demo lab.",
                    safe_metadata={"demo": True, "scenario": f"demo-{index:03d}"},
                    overlap_group=f"demo:{index}",
                )
            )
        db.add(
            PolicyDecision(
                policy_decision_id=demo_id(f"decision:{index}"),
                analysis_id=analysis_id,
                risk_profile_version_id=UUID(SYSTEM_RISK_PROFILE_VERSION_ID),
                phase=event.direction,
                action=action,
                selected_policy_id=None,
                selected_policy_version_id=None,
                scope_winners=[],
                evaluated_policy_versions=[],
                rationale_code=f"demo_{action}",
                created_at=occurred_at + timedelta(milliseconds=10),
            )
        )
        if is_incident:
            assert category is not None
            incident_status = statuses[index % len(statuses)]
            resolved_at = (
                occurred_at + timedelta(hours=2) if incident_status in statuses[2:] else None
            )
            incident = Incident(
                incident_id=demo_id(f"incident:{index}"),
                organization_id=organization_id,
                application_id=application.application_id,
                environment_id=environment.environment_id,
                primary_event_id=event_id,
                primary_analysis_id=analysis_id,
                trigger_rule_id=f"demo:{category.value if category else 'policy'}:{action}",
                status=incident_status,
                severity=severity,
                risk_score=score,
                category=category.value if category else None,
                detector_id=_detector_id(category) if category else None,
                action=action,
                source="gateway",
                direction=event.direction,
                title=f"Synthetic {category.value.replace('_', ' ').title()} review",
                safe_summary="Synthetic demo evidence triggered a deterministic policy action.",
                assignee_user_id=owner.user_id if index % 2 == 0 else None,
                resolution_category=incident_status if resolved_at else None,
                resolution_reason=(
                    "Synthetic scenario reviewed for demonstration." if resolved_at else None
                ),
                privacy_mode="METADATA_ONLY",
                security_retention_days=30,
                version=2 if incident_status != "open" else 1,
                created_at=occurred_at,
                updated_at=resolved_at or occurred_at,
                resolved_at=resolved_at,
            )
            db.add(incident)
            await db.flush()
            incidents.append(incident)
            db.add(
                IncidentSecurityEvent(
                    relation_id=demo_id(f"incident-relation:{index}"),
                    organization_id=organization_id,
                    incident_id=incident.incident_id,
                    event_id=event_id,
                    analysis_id=analysis_id,
                    reason="automatic_policy_escalation",
                    created_at=occurred_at,
                )
            )
            db.add(
                IncidentTimelineEvent(
                    timeline_event_id=demo_id(f"timeline:created:{index}"),
                    organization_id=organization_id,
                    incident_id=incident.incident_id,
                    event_type="incident_created",
                    actor_type="service",
                    actor_user_id=None,
                    safe_summary="Incident created from a synthetic Gateway policy action.",
                    safe_metadata={"demo": True, "action": action},
                    correlation_id=f"demo-{index:03d}",
                    referenced_event_id=event_id,
                    referenced_policy_version_id=None,
                    created_at=occurred_at,
                )
            )
            if index % 3 == 0:
                db.add(
                    IncidentComment(
                        comment_id=demo_id(f"comment:{index}"),
                        organization_id=organization_id,
                        incident_id=incident.incident_id,
                        author_user_id=owner.user_id,
                        body="Synthetic analyst note: deterministic evidence reviewed.",
                        created_at=occurred_at + timedelta(minutes=15),
                    )
                )
    await db.flush()

    provider_calls = 0
    for index in range(8, 16):
        application = applications[index % len(applications)]
        environment_type = ENVIRONMENT_TYPES[index % len(ENVIRONMENT_TYPES)]
        provider = providers[(application.name, environment_type)]
        environment = environments[(application.name, environment_type)]
        db.add(
            GatewayProviderCall(
                gateway_call_id=demo_id(f"provider-call:{index}"),
                organization_id=organization_id,
                application_id=application.application_id,
                environment_id=environment.environment_id,
                provider_id=provider.provider_id,
                input_analysis_id=analyses[index].analysis_id,
                output_analysis_id=None,
                correlation_id=f"demo-provider-{index:03d}",
                configured_model="synthetic-demo-model",
                provider_latency_ms=80 + index,
                status_class=2,
                outcome="completed",
                created_at=seeded_at - timedelta(hours=index * 5),
            )
        )
        provider_calls += 1

    ai_config = AIIntelligenceConfiguration(
        config_id=demo_id("ai-config"),
        organization_id=organization_id,
        application_id=None,
        environment_id=None,
        name="Synthetic advisory provider",
        name_key="synthetic advisory provider",
        kind="openai_compatible_remote",
        base_url="https://advisory.demo.invalid/v1",
        model="synthetic-advisory-model",
        credential_ciphertext=None,
        credential_key_id=None,
        allow_full_content=False,
        connect_timeout_seconds=3,
        request_timeout_seconds=30,
        response_max_bytes=64 * 1024,
        status="disabled",
        created_at=seeded_at,
        updated_at=seeded_at,
    )
    db.add(ai_config)
    await db.flush()
    ai_request = AIIntelligenceRequest(
        request_id=demo_id("ai-request"),
        organization_id=organization_id,
        incident_id=incidents[0].incident_id,
        config_id=ai_config.config_id,
        requested_by_user_id=owner.user_id,
        task_type="incident_summary",
        status="completed",
        context_mode="metadata_only",
        incident_version=incidents[0].version,
        idempotency_key="phase16-demo-summary",
        request_correlation_id="demo-ai-001",
        error_code=None,
        created_at=seeded_at - timedelta(hours=1),
        started_at=seeded_at - timedelta(minutes=59),
        completed_at=seeded_at - timedelta(minutes=58),
    )
    db.add(ai_request)
    await db.flush()
    db.add(
        AIIntelligenceResult(
            result_id=demo_id("ai-result"),
            organization_id=organization_id,
            request_id=ai_request.request_id,
            config_id=ai_config.config_id,
            model="synthetic-advisory-model",
            prompt_template_version="incident-summary-v1",
            input_context_version="1.0.0",
            output_schema_version="1.0.0",
            structured_payload={
                "summary": (
                    "Synthetic advisory summary; deterministic evidence remains authoritative."
                ),
                "key_points": [
                    "A deterministic policy action created this incident.",
                    "This generated text is advisory and cannot change enforcement.",
                ],
            },
            input_tokens=64,
            output_tokens=38,
            total_tokens=102,
            created_at=ai_request.completed_at,
        )
    )
    await db.commit()
    return DemoSummary(
        organization_id=organization_id,
        applications=len(applications),
        environments=len(environments),
        analyses=len(analyses),
        incidents=len(incidents),
        provider_calls=provider_calls,
        ai_results=1,
    )


async def reset_demo(db: AsyncSession) -> bool:
    """Delete only the organization carrying the exact Phase 16 demo marker."""

    organization = await db.scalar(
        select(Organization).where(Organization.slug == DEMO_ORGANIZATION_SLUG)
    )
    if organization is None:
        return False
    _require_demo_organization(organization)
    organization_id = organization.organization_id

    analysis_ids = list(
        (
            await db.scalars(
                select(AnalysisResult.analysis_id)
                .join(SecurityEvent, SecurityEvent.event_id == AnalysisResult.event_id)
                .where(SecurityEvent.organization_id == organization_id)
            )
        ).all()
    )
    policy_version_ids = list(
        (
            await db.scalars(
                select(PolicyVersion.policy_version_id).where(
                    PolicyVersion.organization_id == organization_id
                )
            )
        ).all()
    )
    # These child tables intentionally do not carry organization_id. Delete only rows reached
    # through the already-verified demo tenant before the general tenant-owned pass.
    if analysis_ids:
        await db.execute(
            delete(RiskContribution).where(RiskContribution.analysis_id.in_(analysis_ids))
        )
        await db.execute(delete(PolicyDecision).where(PolicyDecision.analysis_id.in_(analysis_ids)))
        await db.execute(delete(Finding).where(Finding.analysis_id.in_(analysis_ids)))
    if policy_version_ids:
        await db.execute(
            delete(PolicyCondition).where(PolicyCondition.policy_version_id.in_(policy_version_ids))
        )

    # Reverse dependency order keeps this explicit tenant-bounded deletion portable across
    # SQLite tests and PostgreSQL. Tables without organization_id are removed by their
    # contract-defined cascades from tenant-owned parents.
    for table in reversed(Base.metadata.sorted_tables):
        if table.name == Organization.__tablename__:
            continue
        organization_column = table.c.get("organization_id")
        if organization_column is not None:
            await db.execute(delete(table).where(organization_column == organization_id))
    if analysis_ids:
        await db.execute(delete(AnalysisResult).where(AnalysisResult.analysis_id.in_(analysis_ids)))
    await db.execute(delete(SecurityEvent).where(SecurityEvent.organization_id == organization_id))
    await db.execute(delete(Policy).where(Policy.organization_id == organization_id))
    await db.execute(delete(Organization).where(Organization.organization_id == organization_id))
    await db.commit()
    return True


def _require_demo_organization(organization: Organization) -> None:
    if (
        organization.name != DEMO_ORGANIZATION_NAME
        or organization.slug != DEMO_ORGANIZATION_SLUG
        or organization.settings.get("demo_dataset") != DEMO_MARKER
        or organization.settings.get("demo_content") != "synthetic-only"
    ):
        raise DemoSafetyError("refusing operation: the reserved slug is not an exact demo tenant")


async def _summary(
    db: AsyncSession, organization_id: UUID, *, already_present: bool
) -> DemoSummary:
    async def count(model: Any) -> int:
        return int(
            await db.scalar(
                select(func.count())
                .select_from(model)
                .where(model.organization_id == organization_id)
            )
            or 0
        )

    return DemoSummary(
        organization_id=organization_id,
        applications=await count(Application),
        environments=await count(Environment),
        analyses=int(
            await db.scalar(
                select(func.count())
                .select_from(AnalysisResult)
                .join(SecurityEvent, SecurityEvent.event_id == AnalysisResult.event_id)
                .where(SecurityEvent.organization_id == organization_id)
            )
            or 0
        ),
        incidents=await count(Incident),
        provider_calls=await count(GatewayProviderCall),
        ai_results=await count(AIIntelligenceResult),
        already_present=already_present,
    )


def _severity(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _detector_id(category: Category) -> str:
    return {
        Category.PROMPT_INJECTION: "prompt_injection.direct",
        Category.INSTRUCTION_OVERRIDE: "prompt_injection.instruction_override",
        Category.SYSTEM_PROMPT_EXTRACTION: "system_prompt.extraction",
        Category.JAILBREAK: "jailbreak.pattern",
        Category.ROLE_MANIPULATION: "role.manipulation",
        Category.ENCODED_OBFUSCATED: "obfuscation.encoded",
        Category.SECRET_EXPOSURE: "secrets.api_key",
        Category.PII_EXPOSURE: "pii.email",
        Category.SUSPICIOUS_URL: "url.suspicious",
        Category.TOOL_MANIPULATION_INDICATOR: "tool.manipulation_indicator",
        Category.DATA_EXFILTRATION_INDICATOR: "exfiltration.attempt",
    }[category]
