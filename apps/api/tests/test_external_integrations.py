"""Opt-in connectivity checks; never point these variables at production services."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from renzai.core.config import DatabaseConfig, RedisConfig
from renzai.core.errors import RenzaiError
from renzai.core.ids import new_uuid7
from renzai.db import models as _models  # noqa: F401
from renzai.db.session import Database
from renzai.infrastructure.crypto.application_keys import ApplicationKeyCrypto
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.infrastructure.redis.client import RedisClient
from renzai.modules.analytics.application import AnalyticsService
from renzai.modules.analytics.domain import AnalyticsWindow
from renzai.modules.api_keys.models import ApplicationApiKey
from renzai.modules.applications.models import Application
from renzai.modules.environments.models import Environment
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.gateway.rate_limit import RedisGatewayRateLimiter
from renzai.modules.incidents.application import IncidentService
from renzai.modules.incidents.domain import IncidentStatus
from renzai.modules.incidents.models import Incident, IncidentSecurityEvent
from renzai.modules.memberships.domain import MembershipRole
from renzai.modules.memberships.models import Membership
from renzai.modules.organizations.application import OrganizationService
from renzai.modules.organizations.models import Organization
from renzai.modules.policies.models import Policy
from renzai.modules.providers.models import ProviderConfiguration
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent
from renzai.modules.security.rate_limit import RedisAnalyzeRateLimiter
from renzai.modules.users.models import User


@pytest.mark.integration
async def test_postgresql_ping_when_explicit_test_url_is_configured() -> None:
    database_url = os.environ.get("RENZAI_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set RENZAI_TEST_DATABASE_URL to run PostgreSQL connectivity")
    if not database_url.startswith("postgresql+asyncpg://"):
        pytest.fail("RENZAI_TEST_DATABASE_URL must be an asyncpg PostgreSQL URL")
    database = Database(DatabaseConfig(url=database_url, pool_size=1, max_overflow=0))
    try:
        assert await database.ping() is True
    finally:
        await database.close()


@pytest.mark.integration
async def test_redis_ping_when_explicit_test_url_is_configured() -> None:
    redis_url = os.environ.get("RENZAI_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("set RENZAI_TEST_REDIS_URL to run Redis connectivity")
    client = RedisClient(RedisConfig(url=redis_url, required_for_readiness=True))
    try:
        assert await client.ping() is True
        bucket = f"integration-{new_uuid7()}"
        assert await client.increment_window(bucket, 5) == 1
        assert await client.increment_window(bucket, 5) == 2
        limiter = RedisAnalyzeRateLimiter(client, requests=1, window_seconds=5)
        await limiter.check(f"analyze-{bucket}")
        with pytest.raises(RenzaiError) as error:
            await limiter.check(f"analyze-{bucket}")
        assert error.value.code == "rate_limit"
        gateway_limiter = RedisGatewayRateLimiter(client, requests=1, window_seconds=5)
        await gateway_limiter.check(f"gateway-{bucket}")
        with pytest.raises(RenzaiError) as gateway_error:
            await gateway_limiter.check(f"gateway-{bucket}")
        assert gateway_error.value.code == "rate_limit"
    finally:
        await client.close()


@pytest.mark.integration
async def test_postgresql_serializes_competing_owner_demotions() -> None:
    database_url = os.environ.get("RENZAI_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set RENZAI_TEST_DATABASE_URL to run PostgreSQL owner concurrency")
    if not database_url.startswith("postgresql+asyncpg://"):
        pytest.fail("RENZAI_TEST_DATABASE_URL must be an asyncpg PostgreSQL URL")
    database = Database(DatabaseConfig(url=database_url, pool_size=4, max_overflow=0))
    organization_id = new_uuid7()
    first_user_id = new_uuid7()
    second_user_id = new_uuid7()
    first_membership_id = new_uuid7()
    second_membership_id = new_uuid7()
    slug = f"owner-race-{str(organization_id)[:12]}"
    try:
        async with database.session() as setup:
            setup.add_all(
                [
                    User(
                        user_id=first_user_id,
                        email=f"{first_user_id}@example.test",
                        normalized_email=f"{first_user_id}@example.test",
                    ),
                    User(
                        user_id=second_user_id,
                        email=f"{second_user_id}@example.test",
                        normalized_email=f"{second_user_id}@example.test",
                    ),
                    Organization(
                        organization_id=organization_id,
                        name="Owner race integration",
                        slug=slug,
                        settings={"audit_retention_days": 365},
                    ),
                ]
            )
            await setup.flush()
            setup.add_all(
                [
                    Membership(
                        membership_id=first_membership_id,
                        organization_id=organization_id,
                        user_id=first_user_id,
                        role="owner",
                        status="active",
                    ),
                    Membership(
                        membership_id=second_membership_id,
                        organization_id=organization_id,
                        user_id=second_user_id,
                        role="owner",
                        status="active",
                    ),
                ]
            )
            await setup.commit()

        async def demote(actor_id: UUID, target_id: UUID, actor_user_id: UUID) -> str:
            async with database.session() as session:
                actor = await session.get(Membership, actor_id)
                actor_user = await session.get(User, actor_user_id)
                assert actor is not None and actor_user is not None
                service = OrganizationService(
                    session,
                    IdentityCrypto("integration-only-key-material-000000", "v1"),
                    168,
                    365,
                )
                try:
                    await service.change_member_role(
                        organization_id, actor, actor_user, target_id, MembershipRole.ADMIN
                    )
                except RenzaiError as error:
                    await session.rollback()
                    return error.code
                return "success"

        outcomes = await asyncio.gather(
            demote(first_membership_id, second_membership_id, first_user_id),
            demote(second_membership_id, first_membership_id, second_user_id),
        )
        assert outcomes.count("success") == 1
        async with database.session() as verify:
            owner_count = await verify.scalar(
                select(func.count())
                .select_from(Membership)
                .where(
                    Membership.organization_id == organization_id,
                    Membership.status == "active",
                    Membership.role == "owner",
                )
            )
            assert owner_count == 1
    finally:
        async with database.session() as cleanup:
            await cleanup.execute(
                delete(Organization).where(Organization.organization_id == organization_id)
            )
            await cleanup.execute(
                delete(User).where(User.user_id.in_([first_user_id, second_user_id]))
            )
            await cleanup.commit()
        await database.close()


@pytest.mark.integration
async def test_postgresql_phase6_constraints_and_analysis_persistence() -> None:
    database_url = os.environ.get("RENZAI_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set RENZAI_TEST_DATABASE_URL to run PostgreSQL Phase 6 integration")
    database = Database(DatabaseConfig(url=database_url, pool_size=2, max_overflow=0))
    user_id = new_uuid7()
    organization_id = new_uuid7()
    other_organization_id = new_uuid7()
    application_id = new_uuid7()
    environment_id = new_uuid7()
    event_id = new_uuid7()
    analysis_id = new_uuid7()
    crypto = ApplicationKeyCrypto("integration-application-key-root-0001", "v1")
    issued = crypto.issue("development")
    try:
        async with database.session() as setup:
            setup.add(
                User(
                    user_id=user_id,
                    email=f"{user_id}@example.test",
                    normalized_email=f"{user_id}@example.test",
                )
            )
            setup.add_all(
                [
                    Organization(
                        organization_id=organization_id,
                        name="Phase 6 integration",
                        slug=f"phase6-{str(organization_id)[:12]}",
                        settings={"audit_retention_days": 365},
                    ),
                    Organization(
                        organization_id=other_organization_id,
                        name="Phase 6 other",
                        slug=f"phase6-other-{str(other_organization_id)[:12]}",
                        settings={"audit_retention_days": 365},
                    ),
                ]
            )
            await setup.flush()
            setup.add(
                Application(
                    application_id=application_id,
                    organization_id=organization_id,
                    name="Detector app",
                    name_key="detector app",
                )
            )
            await setup.flush()
            setup.add(
                Environment(
                    environment_id=environment_id,
                    organization_id=organization_id,
                    application_id=application_id,
                    type="development",
                )
            )
            await setup.flush()
            setup.add(
                ApplicationApiKey(
                    organization_id=organization_id,
                    application_id=application_id,
                    environment_id=environment_id,
                    created_by_user_id=user_id,
                    label="integration",
                    lookup=issued.lookup,
                    prefix=issued.prefix,
                    verifier=issued.verifier,
                    verifier_key_id="v1",
                )
            )
            setup.add(
                SecurityEvent(
                    event_id=event_id,
                    organization_id=organization_id,
                    application_id=application_id,
                    environment_id=environment_id,
                    direction="input",
                    source="analyze",
                    correlation_id=str(new_uuid7()),
                    privacy_mode="REDACTED",
                    content="[REDACTED:EMAIL]",
                    content_bytes=16,
                    retention_days=30,
                )
            )
            await setup.flush()
            setup.add(
                AnalysisResult(
                    analysis_id=analysis_id,
                    event_id=event_id,
                    normalization_version="1.0.0",
                    ruleset_version="1.0.0",
                    finding_count=1,
                    normalization_ms=1,
                    detector_ms=1,
                    total_ms=2,
                    capabilities={"detection": True},
                )
            )
            await setup.flush()
            setup.add(
                Finding(
                    analysis_id=analysis_id,
                    detector_id="pii.email",
                    detector_version="1.0.0",
                    ruleset_version="1.0.0",
                    category="pii_exposure",
                    direction="input",
                    severity="medium",
                    confidence=98,
                    evidence={"kind": "redacted_excerpt", "text": "[REDACTED:EMAIL]"},
                    safe_explanation="An email address was detected and redacted.",
                    safe_metadata={"rule_id": "email"},
                )
            )
            await setup.commit()

        async with database.session() as verify:
            assert await verify.scalar(select(func.count()).select_from(SecurityEvent)) >= 1
            assert await verify.scalar(select(func.count()).select_from(Finding)) >= 1

        async with database.session() as invalid_tenant:
            invalid_tenant.add(
                Environment(
                    organization_id=other_organization_id,
                    application_id=application_id,
                    type="staging",
                )
            )
            with pytest.raises(IntegrityError):
                await invalid_tenant.commit()
            await invalid_tenant.rollback()

        async with database.session() as duplicate:
            duplicate.add(
                Environment(
                    organization_id=organization_id,
                    application_id=application_id,
                    type="development",
                )
            )
            with pytest.raises(IntegrityError):
                await duplicate.commit()
            await duplicate.rollback()
    finally:
        async with database.session() as cleanup:
            await cleanup.execute(
                delete(Organization).where(
                    Organization.organization_id.in_([organization_id, other_organization_id])
                )
            )
            await cleanup.execute(delete(User).where(User.user_id == user_id))
            await cleanup.commit()
        await database.close()


@pytest.mark.integration
async def test_postgresql_phase7_duplicate_priority_race() -> None:
    database_url = os.environ.get("RENZAI_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set RENZAI_TEST_DATABASE_URL to run PostgreSQL Phase 7 priority race")
    if not database_url.startswith("postgresql+asyncpg://"):
        pytest.fail("RENZAI_TEST_DATABASE_URL must be an asyncpg PostgreSQL URL")
    database = Database(DatabaseConfig(url=database_url, pool_size=4, max_overflow=0))
    organization_id = new_uuid7()
    application_id = new_uuid7()
    try:
        async with database.session() as setup:
            setup.add(
                Organization(
                    organization_id=organization_id,
                    name="Phase 7 priority race",
                    slug=f"phase7-race-{str(organization_id)[:12]}",
                    settings={"audit_retention_days": 365},
                )
            )
            await setup.flush()
            setup.add(
                Application(
                    application_id=application_id,
                    organization_id=organization_id,
                    name="Policy race",
                    name_key="policy race",
                )
            )
            await setup.commit()

        async def create_competing_policy(label: str) -> str:
            async with database.session() as session:
                session.add(
                    Policy(
                        organization_id=organization_id,
                        application_id=application_id,
                        environment_id=None,
                        scope_kind="application",
                        scope_id=application_id,
                        name=label,
                        phase="input",
                        priority=912_345,
                        enabled=False,
                        active_version=1,
                        status="active",
                        is_baseline=False,
                    )
                )
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    return "conflict"
                return "success"

        outcomes = await asyncio.gather(
            create_competing_policy("Race A"), create_competing_policy("Race B")
        )
        assert sorted(outcomes) == ["conflict", "success"]
        async with database.session() as verify:
            count = await verify.scalar(
                select(func.count())
                .select_from(Policy)
                .where(
                    Policy.organization_id == organization_id,
                    Policy.scope_id == application_id,
                    Policy.phase == "input",
                    Policy.priority == 912_345,
                )
            )
            assert count == 1
    finally:
        async with database.session() as cleanup:
            await cleanup.execute(
                delete(Organization).where(Organization.organization_id == organization_id)
            )
            await cleanup.commit()
        await database.close()


@pytest.mark.integration
async def test_postgresql_phase8_provider_constraints() -> None:
    database_url = os.environ.get("RENZAI_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set RENZAI_TEST_DATABASE_URL to run PostgreSQL Phase 8 constraints")
    if not database_url.startswith("postgresql+asyncpg://"):
        pytest.fail("RENZAI_TEST_DATABASE_URL must be an asyncpg PostgreSQL URL")
    database = Database(DatabaseConfig(url=database_url, pool_size=2, max_overflow=0))
    organization_id = new_uuid7()
    other_organization_id = new_uuid7()
    application_id = new_uuid7()
    environment_id = new_uuid7()
    try:
        async with database.session() as setup:
            setup.add_all(
                [
                    Organization(
                        organization_id=organization_id,
                        name="Phase 8 provider constraints",
                        slug=f"phase8-{str(organization_id)[:12]}",
                        settings={"audit_retention_days": 365},
                    ),
                    Organization(
                        organization_id=other_organization_id,
                        name="Phase 8 other tenant",
                        slug=f"phase8-other-{str(other_organization_id)[:12]}",
                        settings={"audit_retention_days": 365},
                    ),
                ]
            )
            await setup.flush()
            setup.add(
                Application(
                    application_id=application_id,
                    organization_id=organization_id,
                    name="Gateway",
                    name_key="gateway",
                )
            )
            await setup.flush()
            setup.add(
                Environment(
                    environment_id=environment_id,
                    organization_id=organization_id,
                    application_id=application_id,
                    type="development",
                )
            )
            await setup.flush()
            setup.add(
                ProviderConfiguration(
                    organization_id=organization_id,
                    application_id=application_id,
                    environment_id=environment_id,
                    kind="openai_compatible_remote",
                    name="Primary",
                    name_key="primary",
                    base_url="https://provider.example",
                    model="test-model",
                    credential_ciphertext=b"encrypted-only",
                    credential_key_id="provider-v1",
                    supports_seed=False,
                    max_tokens=4096,
                    connect_timeout_seconds=3,
                    chat_timeout_seconds=30,
                    health_timeout_seconds=5,
                    response_max_bytes=128 * 1024,
                    status="active",
                    validation_policy_version="1.0.0",
                    last_validation_status="never",
                )
            )
            await setup.commit()

        async with database.session() as duplicate:
            duplicate.add(
                ProviderConfiguration(
                    organization_id=organization_id,
                    application_id=application_id,
                    environment_id=environment_id,
                    kind="openai_compatible_local",
                    name="PRIMARY",
                    name_key="primary",
                    base_url="http://localhost:11434",
                    model="test-model",
                    supports_seed=False,
                    max_tokens=4096,
                    connect_timeout_seconds=3,
                    chat_timeout_seconds=30,
                    health_timeout_seconds=5,
                    response_max_bytes=128 * 1024,
                    status="active",
                    validation_policy_version="1.0.0",
                    last_validation_status="never",
                )
            )
            with pytest.raises(IntegrityError):
                await duplicate.commit()
            await duplicate.rollback()

        async with database.session() as wrong_tenant:
            wrong_tenant.add(
                ProviderConfiguration(
                    organization_id=other_organization_id,
                    application_id=application_id,
                    environment_id=environment_id,
                    kind="openai_compatible_remote",
                    name="Wrong tenant",
                    name_key="wrong tenant",
                    base_url="https://provider.example",
                    model="test-model",
                    supports_seed=False,
                    max_tokens=4096,
                    connect_timeout_seconds=3,
                    chat_timeout_seconds=30,
                    health_timeout_seconds=5,
                    response_max_bytes=128 * 1024,
                    status="active",
                    validation_policy_version="1.0.0",
                    last_validation_status="never",
                )
            )
            with pytest.raises(IntegrityError):
                await wrong_tenant.commit()
            await wrong_tenant.rollback()
    finally:
        async with database.session() as cleanup:
            await cleanup.execute(
                delete(Organization).where(
                    Organization.organization_id.in_([organization_id, other_organization_id])
                )
            )
            await cleanup.commit()
        await database.close()


@pytest.mark.integration
async def test_postgresql_phase9_incident_deduplication_and_status_concurrency() -> None:
    database_url = os.environ.get("RENZAI_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set RENZAI_TEST_DATABASE_URL to run PostgreSQL Phase 9 concurrency")
    if not database_url.startswith("postgresql+asyncpg://"):
        pytest.fail("RENZAI_TEST_DATABASE_URL must be an asyncpg PostgreSQL URL")
    database = Database(DatabaseConfig(url=database_url, pool_size=6, max_overflow=0))
    organization_id = new_uuid7()
    application_id = new_uuid7()
    environment_id = new_uuid7()
    event_id = new_uuid7()
    analysis_id = new_uuid7()
    user_id = new_uuid7()
    membership_id = new_uuid7()
    try:
        async with database.session() as setup:
            setup.add_all(
                [
                    User(
                        user_id=user_id,
                        email=f"phase9-{user_id}@example.test",
                        normalized_email=f"phase9-{user_id}@example.test",
                    ),
                    Organization(
                        organization_id=organization_id,
                        name="Phase 9 incident concurrency",
                        slug=f"phase9-{str(organization_id)[:12]}",
                        settings={"audit_retention_days": 365},
                    ),
                ]
            )
            await setup.flush()
            setup.add_all(
                [
                    Membership(
                        membership_id=membership_id,
                        organization_id=organization_id,
                        user_id=user_id,
                        role="security_analyst",
                        status="active",
                    ),
                    Application(
                        application_id=application_id,
                        organization_id=organization_id,
                        name="Incident Gateway",
                        name_key="incident gateway",
                    ),
                ]
            )
            await setup.flush()
            setup.add(
                Environment(
                    environment_id=environment_id,
                    organization_id=organization_id,
                    application_id=application_id,
                    type="production",
                )
            )
            await setup.flush()
            setup.add(
                SecurityEvent(
                    event_id=event_id,
                    organization_id=organization_id,
                    application_id=application_id,
                    environment_id=environment_id,
                    direction="input",
                    source="gateway",
                    correlation_id=f"phase9-{event_id}",
                    privacy_mode="METADATA_ONLY",
                    content=None,
                    content_bytes=12,
                    retention_days=30,
                    action="block",
                    risk_score=84,
                    risk_severity="high",
                )
            )
            await setup.flush()
            setup.add(
                AnalysisResult(
                    analysis_id=analysis_id,
                    event_id=event_id,
                    normalization_version="1.0.0",
                    ruleset_version="1.0.0",
                    status="completed",
                    finding_count=0,
                    normalization_ms=1,
                    detector_ms=1,
                    total_ms=2,
                    capabilities={},
                    risk_score=84,
                    risk_severity="high",
                    risk_confidence=90,
                    base_score=84,
                    corroboration_bonus=0,
                    critical_floor=0,
                    action="block",
                    risk_ms=0,
                    policy_ms=0,
                )
            )
            await setup.commit()

        async def escalate(correlation_id: str) -> str:
            async with database.session() as session:
                incident = await IncidentService(session).create_from_analysis(
                    organization_id, analysis_id, correlation_id
                )
                return str(incident.incident_id)

        first_id, second_id = await asyncio.gather(escalate("race-a"), escalate("race-b"))
        assert first_id == second_id
        async with database.session() as verify:
            incidents = list(
                (
                    await verify.execute(
                        select(Incident).where(Incident.organization_id == organization_id)
                    )
                ).scalars()
            )
            assert len(incidents) == 1
            incident_id = incidents[0].incident_id

        async def transition(target: IncidentStatus) -> str:
            async with database.session() as session:
                actor = await session.get(Membership, membership_id)
                user = await session.get(User, user_id)
                assert actor is not None and user is not None
                try:
                    await IncidentService(session).transition(
                        actor, user, incident_id, target, 1, None
                    )
                except RenzaiError as error:
                    await session.rollback()
                    return error.code
                return "success"

        outcomes = await asyncio.gather(
            transition(IncidentStatus.INVESTIGATING), transition(IncidentStatus.RESOLVED)
        )
        assert sorted(outcomes) == ["conflict", "success"]
        async with database.session() as retention:
            await retention.execute(delete(SecurityEvent).where(SecurityEvent.event_id == event_id))
            await retention.commit()
        async with database.session() as retained:
            assert await retained.get(Incident, incident_id) is not None
            relation_count = await retained.scalar(
                select(func.count())
                .select_from(IncidentSecurityEvent)
                .where(IncidentSecurityEvent.incident_id == incident_id)
            )
            assert relation_count == 0
    finally:
        async with database.session() as cleanup:
            await cleanup.execute(
                delete(Incident).where(Incident.organization_id == organization_id)
            )
            await cleanup.execute(
                delete(Organization).where(Organization.organization_id == organization_id)
            )
            await cleanup.commit()
        await database.close()


@pytest.mark.integration
async def test_postgresql_phase10_bucketing_distinct_counts_filters_and_tenant_scope() -> None:
    database_url = os.environ.get("RENZAI_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set RENZAI_TEST_DATABASE_URL to run PostgreSQL Phase 10 analytics")
    if not database_url.startswith("postgresql+asyncpg://"):
        pytest.fail("RENZAI_TEST_DATABASE_URL must be an asyncpg PostgreSQL URL")
    database = Database(DatabaseConfig(url=database_url, pool_size=2, max_overflow=0))
    organization_id = new_uuid7()
    other_organization_id = new_uuid7()
    application_id = new_uuid7()
    environment_id = new_uuid7()
    other_application_id = new_uuid7()
    other_environment_id = new_uuid7()
    provider_id = new_uuid7()
    as_of = datetime(2026, 10, 1, 12, 30, tzinfo=UTC)
    try:
        async with database.session() as session:
            session.add_all(
                [
                    Organization(
                        organization_id=organization_id,
                        name="Phase 10 analytics",
                        slug=f"phase10-{str(organization_id)[:12]}",
                        settings={"audit_retention_days": 365},
                    ),
                    Organization(
                        organization_id=other_organization_id,
                        name="Phase 10 other tenant",
                        slug=f"phase10-other-{str(other_organization_id)[:12]}",
                        settings={"audit_retention_days": 365},
                    ),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    Application(
                        application_id=application_id,
                        organization_id=organization_id,
                        name="Analytics app",
                        name_key="analytics app",
                    ),
                    Application(
                        application_id=other_application_id,
                        organization_id=other_organization_id,
                        name="Other app",
                        name_key="other app",
                    ),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    Environment(
                        environment_id=environment_id,
                        organization_id=organization_id,
                        application_id=application_id,
                        type="production",
                    ),
                    Environment(
                        environment_id=other_environment_id,
                        organization_id=other_organization_id,
                        application_id=other_application_id,
                        type="production",
                    ),
                ]
            )
            await session.flush()
            session.add(
                ProviderConfiguration(
                    provider_id=provider_id,
                    organization_id=organization_id,
                    application_id=application_id,
                    environment_id=environment_id,
                    kind="openai_compatible_local",
                    name="Analytics provider",
                    name_key="analytics provider",
                    base_url="http://127.0.0.1:11434/v1",
                    model="safe-model",
                )
            )
            await session.flush()

            async def add_analysis(
                org_id: UUID,
                app_id: UUID,
                env_id: UUID,
                occurred_at: datetime,
                *,
                findings: int,
                source: str = "analyze",
            ) -> AnalysisResult:
                event = SecurityEvent(
                    organization_id=org_id,
                    application_id=app_id,
                    environment_id=env_id,
                    direction="input",
                    source=source,
                    occurred_at=occurred_at,
                    correlation_id=f"phase10-{new_uuid7()}",
                    privacy_mode="METADATA_ONLY",
                    content=None,
                    content_bytes=0,
                    retention_days=30,
                    action="block" if findings else "allow",
                    risk_score=75 if findings else 0,
                    risk_severity="high" if findings else "low",
                )
                session.add(event)
                await session.flush()
                analysis = AnalysisResult(
                    event_id=event.event_id,
                    normalization_version="1.0.0",
                    ruleset_version="1.0.0",
                    status="completed",
                    finding_count=findings,
                    normalization_ms=1,
                    detector_ms=1,
                    total_ms=2,
                    capabilities={},
                    risk_score=75 if findings else 0,
                    risk_severity="high" if findings else "low",
                    risk_confidence=90,
                    base_score=75 if findings else 0,
                    corroboration_bonus=0,
                    critical_floor=0,
                    action="block" if findings else "allow",
                    risk_ms=0,
                    policy_ms=0,
                )
                session.add(analysis)
                await session.flush()
                for index in range(findings):
                    session.add(
                        Finding(
                            analysis_id=analysis.analysis_id,
                            detector_id="phase10-detector",
                            detector_version="1.0.0",
                            ruleset_version="1.0.0",
                            category="prompt_injection",
                            direction="input",
                            severity="high",
                            confidence=90 + index,
                            evidence={},
                            safe_explanation="Safe aggregate metadata.",
                            safe_metadata={},
                        )
                    )
                return analysis

            gateway_input = await add_analysis(
                organization_id,
                application_id,
                environment_id,
                as_of - timedelta(hours=2),
                findings=2,
                source="gateway",
            )
            gateway_output = await add_analysis(
                organization_id,
                application_id,
                environment_id,
                as_of - timedelta(hours=2),
                findings=0,
                source="gateway",
            )
            await add_analysis(
                organization_id,
                application_id,
                environment_id,
                as_of - timedelta(hours=1),
                findings=1,
            )
            await add_analysis(
                other_organization_id,
                other_application_id,
                other_environment_id,
                as_of - timedelta(hours=1),
                findings=1,
            )
            session.add(
                GatewayProviderCall(
                    organization_id=organization_id,
                    application_id=application_id,
                    environment_id=environment_id,
                    provider_id=provider_id,
                    input_analysis_id=gateway_input.analysis_id,
                    output_analysis_id=gateway_output.analysis_id,
                    correlation_id="phase10-postgresql",
                    configured_model="safe-model",
                    provider_latency_ms=20,
                    status_class=2,
                    outcome="completed",
                    created_at=as_of - timedelta(hours=2),
                )
            )
            await session.flush()
            body = await AnalyticsService(session, as_of=as_of).dashboard(
                organization_id,
                window=AnalyticsWindow.HOURS_24,
                application_id=application_id,
                environment_id=environment_id,
            )
            assert body["summary"] == {
                "analyses": 3,
                "gateway_requests": 1,
                "threats_detected": 2,
                "blocked": 2,
                "require_review": 0,
                "redacted": 0,
                "critical_analyses": 0,
                "open_incidents": 0,
                "threat_rate_numerator": 2,
                "threat_rate_denominator": 3,
                "threat_rate_percent": 66.67,
            }
            categories = body["threat_categories"]
            assert isinstance(categories, list)
            assert categories == [
                {
                    "category": "prompt_injection",
                    "finding_count": 3,
                    "affected_analyses": 2,
                }
            ]
            activity = body["activity"]
            assert isinstance(activity, list)
            assert len(activity) == 24
            assert (
                sum(int(item["analysis_count"]) for item in activity if isinstance(item, dict)) == 3
            )
            gateway = await AnalyticsService(session, as_of=as_of).dashboard(
                organization_id,
                window=AnalyticsWindow.HOURS_24,
                application_id=application_id,
                environment_id=environment_id,
                source=None,
            )
            assert gateway["providers"]
            await session.commit()
    finally:
        async with database.session() as cleanup:
            await cleanup.execute(
                delete(GatewayProviderCall).where(
                    GatewayProviderCall.organization_id.in_(
                        [organization_id, other_organization_id]
                    )
                )
            )
            await cleanup.execute(
                delete(Organization).where(
                    Organization.organization_id.in_([organization_id, other_organization_id])
                )
            )
            await cleanup.commit()
        await database.close()
