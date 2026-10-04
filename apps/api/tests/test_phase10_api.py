from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.config import Settings
from renzai.core.ids import new_uuid7
from renzai.modules.analytics.application import AnalyticsService
from renzai.modules.analytics.domain import AnalyticsWindow, window_range
from renzai.modules.audit.models import AuditEvent
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.incidents.models import Incident
from renzai.modules.memberships.models import Membership
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent
from test_phase8_api import (  # type: ignore[import-not-found]
    FakeProvider,
    bootstrap,
    create_provider,
    gateway,
    phase8_client,  # noqa: F401 - imported pytest fixture
    run_db,
)


@pytest.fixture
def phase10_client(
    request: pytest.FixtureRequest,
) -> tuple[TestClient, Settings, FakeProvider]:
    return request.getfixturevalue("phase8_client")  # type: ignore[no-any-return]


def dashboard_path(organization_id: str) -> str:
    return f"/api/v1/organizations/{organization_id}/analytics/dashboard"


async def seed_dashboard(
    session: AsyncSession,
    *,
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
    provider_id: UUID,
    occurred_at: datetime,
) -> None:
    analyses: list[AnalysisResult] = []
    actions = (
        "allow",
        "flag",
        "block",
        "redact",
        "require_review",
        "allow",
        "allow",
        "allow",
        "allow",
        "allow",
    )
    severities = (
        "critical",
        "high",
        "medium",
        "low",
        "critical",
        "low",
        "medium",
        "high",
        "low",
        "low",
    )
    for index, (action, severity) in enumerate(zip(actions, severities, strict=True)):
        event_id = new_uuid7()
        analysis_id = new_uuid7()
        source = "gateway" if index < 2 else ("playground" if index == 2 else "analyze")
        event = SecurityEvent(
            event_id=event_id,
            organization_id=organization_id,
            application_id=application_id,
            environment_id=environment_id,
            direction="input" if index != 1 else "output",
            source=source,
            occurred_at=occurred_at - timedelta(minutes=index),
            correlation_id=f"phase10-{index}",
            privacy_mode="METADATA_ONLY",
            content=None,
            content_bytes=20,
            retention_days=30,
            action=action,
            risk_score=90 if severity == "critical" else 25,
            risk_severity=severity,
        )
        finding_count = 2 if index == 0 else (1 if index < 4 else 0)
        analysis = AnalysisResult(
            analysis_id=analysis_id,
            event_id=event_id,
            completed_at=occurred_at,
            normalization_version="1.0.0",
            ruleset_version="1.0.0",
            status="completed",
            finding_count=finding_count,
            normalization_ms=1,
            detector_ms=2,
            total_ms=3,
            capabilities={},
            risk_score=90 if severity == "critical" else 25,
            risk_severity=severity,
            risk_confidence=90,
            base_score=25,
            corroboration_bonus=0,
            critical_floor=0,
            action=action,
            risk_ms=1,
            policy_ms=1,
        )
        session.add_all([event, analysis])
        analyses.append(analysis)
        for duplicate in range(finding_count):
            session.add(
                Finding(
                    analysis_id=analysis_id,
                    detector_id="prompt-injection",
                    detector_version="1.0.0",
                    ruleset_version="1.0.0",
                    category="prompt_injection" if index == 0 else "sensitive_data",
                    direction=event.direction,
                    severity="high",
                    confidence=80 + duplicate,
                    evidence={},
                    safe_explanation="Safe detector metadata.",
                    safe_metadata={},
                )
            )
    session.add(
        GatewayProviderCall(
            organization_id=organization_id,
            application_id=application_id,
            environment_id=environment_id,
            provider_id=provider_id,
            input_analysis_id=analyses[0].analysis_id,
            output_analysis_id=analyses[1].analysis_id,
            correlation_id="phase10-gateway",
            configured_model="safe-model",
            provider_latency_ms=42,
            status_class=2,
            outcome="completed",
            created_at=occurred_at,
        )
    )
    outcomes = (
        "provider_timeout",
        "provider_error",
        "configuration_error",
        "output_block",
        "output_review",
        "output_inspection_failure",
    )
    for index, outcome in enumerate(outcomes, start=1):
        session.add(
            GatewayProviderCall(
                organization_id=organization_id,
                application_id=application_id,
                environment_id=environment_id,
                provider_id=provider_id,
                input_analysis_id=analyses[0].analysis_id,
                correlation_id=f"phase10-provider-{index}",
                configured_model="safe-model",
                provider_latency_ms=40 + index,
                outcome=outcome,
                created_at=occurred_at,
            )
        )
    statuses = ("open", "investigating", "resolved", "ignored", "false_positive")
    for index, status in enumerate(statuses):
        session.add(
            Incident(
                organization_id=organization_id,
                application_id=application_id,
                environment_id=environment_id,
                manual_idempotency_key=f"phase10-{status}",
                status=status,
                severity="critical" if status == "open" else "medium",
                source="manual",
                title=f"Safe {status} incident",
                safe_summary="Safe aggregate test metadata.",
                version=1,
                created_at=occurred_at - timedelta(seconds=index),
                updated_at=occurred_at,
            )
        )


@pytest.mark.e2e
def test_dashboard_exact_metrics_and_bounded_safe_response(
    phase10_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, _fake = phase10_client
    organization_id, csrf, app, env, _key = bootstrap(client)
    provider = create_provider(client, organization_id, csrf, app, env)
    run_db(
        settings,
        lambda session: seed_dashboard(
            session,
            organization_id=UUID(organization_id),
            application_id=UUID(str(app["application_id"])),
            environment_id=UUID(str(env["environment_id"])),
            provider_id=UUID(str(provider["provider_id"])),
            occurred_at=datetime.now(UTC) - timedelta(minutes=5),
        ),
    )

    async def audit_count(session: AsyncSession) -> int:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.organization_id == UUID(organization_id))
            )
            or 0
        )

    before_audit_count = run_db(settings, audit_count)
    response = client.get(dashboard_path(organization_id))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == {
        "analyses": 10,
        "gateway_requests": 7,
        "threats_detected": 4,
        "blocked": 1,
        "require_review": 1,
        "redacted": 1,
        "critical_analyses": 2,
        "open_incidents": 1,
        "threat_rate_numerator": 4,
        "threat_rate_denominator": 10,
        "threat_rate_percent": 40.0,
    }
    assert len(body["activity"]) == 24
    assert sum(item["analysis_count"] for item in body["activity"]) == 10
    assert body["risk_distribution"] == [
        {"severity": "low", "count": 4},
        {"severity": "medium", "count": 2},
        {"severity": "high", "count": 2},
        {"severity": "critical", "count": 2},
    ]
    assert body["policy_actions"] == [
        {"action": "allow", "count": 6},
        {"action": "flag", "count": 1},
        {"action": "redact", "count": 1},
        {"action": "require_review", "count": 1},
        {"action": "block", "count": 1},
    ]
    category = next(
        item for item in body["threat_categories"] if item["category"] == "prompt_injection"
    )
    assert category == {
        "category": "prompt_injection",
        "finding_count": 2,
        "affected_analyses": 1,
    }
    assert body["providers"][0]["request_count"] == 7
    for outcome in (
        "completed",
        "provider_timeout",
        "provider_error",
        "configuration_error",
        "output_block",
        "output_review",
        "output_inspection_failure",
    ):
        assert body["providers"][0][outcome] == 1
    assert body["incidents"]["statuses"] == [
        {"status": status, "count": 1}
        for status in ("open", "investigating", "resolved", "ignored", "false_positive")
    ]
    serialized = response.text.lower()
    for forbidden in ("prompt text", "provider-secret-value", "evidence", "safe_summary"):
        assert forbidden not in serialized
    assert run_db(settings, audit_count) == before_audit_count


def test_gateway_request_is_not_double_counted_and_source_filter_is_consistent(
    phase10_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, _fake = phase10_client
    organization_id, csrf, app, env, _key = bootstrap(client)
    provider = create_provider(client, organization_id, csrf, app, env)
    run_db(
        settings,
        lambda session: seed_dashboard(
            session,
            organization_id=UUID(organization_id),
            application_id=UUID(str(app["application_id"])),
            environment_id=UUID(str(env["environment_id"])),
            provider_id=UUID(str(provider["provider_id"])),
            occurred_at=datetime.now(UTC) - timedelta(minutes=5),
        ),
    )
    gateway_only = client.get(dashboard_path(organization_id), params={"source": "gateway"}).json()
    assert gateway_only["summary"]["analyses"] == 2
    assert gateway_only["summary"]["gateway_requests"] == 7
    assert gateway_only["providers"][0]["request_count"] == 7
    analyze_only = client.get(dashboard_path(organization_id), params={"source": "analyze"}).json()
    assert analyze_only["summary"]["analyses"] == 7
    assert analyze_only["summary"]["gateway_requests"] == 0
    assert analyze_only["providers"] == []


def test_one_real_gateway_request_counts_one_request_and_two_analyses(
    phase10_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, _settings, _fake = phase10_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)

    assert gateway(client, key).status_code == 200
    summary = client.get(dashboard_path(organization_id)).json()["summary"]

    assert summary["gateway_requests"] == 1
    assert summary["analyses"] == 2


@pytest.mark.parametrize("role", ["owner", "admin", "security_analyst", "developer", "viewer"])
def test_all_contract_roles_can_read_empty_dashboard(
    phase10_client: tuple[TestClient, Settings, FakeProvider], role: str
) -> None:
    client, settings, _fake = phase10_client
    organization_id, _csrf, _app, _env, _key = bootstrap(client)

    async def set_role(session: AsyncSession) -> None:
        await session.execute(
            update(Membership)
            .where(Membership.organization_id == UUID(organization_id))
            .values(role=role)
        )

    run_db(settings, set_role)
    response = client.get(dashboard_path(organization_id))
    assert response.status_code == 200
    assert response.json()["summary"]["analyses"] == 0
    assert response.json()["summary"]["threat_rate_denominator"] == 0
    assert response.json()["summary"]["threat_rate_percent"] == 0.0
    assert len(response.json()["activity"]) == 24


def test_foreign_filters_are_hidden_and_environment_requires_application(
    phase10_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, _settings, _fake = phase10_client
    organization_id, _csrf, _app, env, _key = bootstrap(client)
    foreign_application = new_uuid7()
    assert (
        client.get(
            dashboard_path(organization_id),
            params={"application_id": str(foreign_application)},
        ).status_code
        == 404
    )
    assert (
        client.get(
            dashboard_path(organization_id),
            params={"environment_id": str(env["environment_id"])},
        ).status_code
        == 422
    )


def test_fixed_time_boundaries_tenant_scope_filters_and_zero_buckets(
    phase10_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, _fake = phase10_client
    organization_id, _csrf, app, env, _key = bootstrap(client)
    as_of = datetime(2026, 10, 1, 12, 34, tzinfo=UTC)
    selected = window_range(AnalyticsWindow.HOURS_24, as_of)

    async def seed_and_query(session: AsyncSession) -> dict[str, object]:
        for index, timestamp in enumerate(
            (
                selected.start - timedelta(microseconds=1),
                selected.start,
                selected.start + timedelta(hours=4),
                selected.end,
                selected.end + timedelta(microseconds=1),
            )
        ):
            event = SecurityEvent(
                organization_id=UUID(organization_id),
                application_id=UUID(str(app["application_id"])),
                environment_id=UUID(str(env["environment_id"])),
                direction="input",
                source="analyze",
                occurred_at=timestamp,
                correlation_id=f"boundary-{index}",
                privacy_mode="METADATA_ONLY",
                content=None,
                content_bytes=0,
                retention_days=30,
                action="allow",
                risk_score=0,
                risk_severity="low",
            )
            session.add(event)
            await session.flush()
            session.add(
                AnalysisResult(
                    event_id=event.event_id,
                    completed_at=timestamp,
                    normalization_version="1.0.0",
                    ruleset_version="1.0.0",
                    status="completed",
                    finding_count=0,
                    normalization_ms=0,
                    detector_ms=0,
                    total_ms=0,
                    capabilities={},
                    risk_score=0,
                    risk_severity="low",
                    risk_confidence=100,
                    base_score=0,
                    corroboration_bonus=0,
                    critical_floor=0,
                    action="allow",
                    risk_ms=0,
                    policy_ms=0,
                )
            )
        await session.flush()
        return await AnalyticsService(session, as_of=as_of).dashboard(
            UUID(organization_id),
            window=AnalyticsWindow.HOURS_24,
            application_id=UUID(str(app["application_id"])),
            environment_id=UUID(str(env["environment_id"])),
        )

    body = run_db(settings, seed_and_query)
    summary = body["summary"]
    assert isinstance(summary, dict)
    assert summary["analyses"] == 3
    activity = body["activity"]
    assert isinstance(activity, list)
    assert len(activity) == 24
    assert sum(int(item["analysis_count"]) for item in activity if isinstance(item, dict)) == 3
    assert (
        sum(1 for item in activity if isinstance(item, dict) and item["analysis_count"] == 0) == 21
    )
