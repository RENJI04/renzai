from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.core.config import Settings
from renzai.core.ids import new_uuid7
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.incidents.application import IncidentPersistenceFailure, IncidentService
from renzai.modules.incidents.domain import (
    IncidentStatus,
    InvalidIncidentTransition,
    validate_transition,
)
from renzai.modules.incidents.models import (
    Incident,
    IncidentComment,
    IncidentSecurityEvent,
    IncidentTimelineEvent,
)
from renzai.modules.memberships.models import Membership
from renzai.modules.policies.models import PolicyDecision
from renzai.modules.risk.models import RiskContribution
from renzai.modules.security.models import AnalysisResult, Finding, SecurityEvent
from renzai.modules.users.models import User
from test_phase8_api import (  # type: ignore[import-not-found]
    FakeProvider,
    bootstrap,
    create_policy,
    create_provider,
    gateway,
    phase8_client,  # noqa: F401 - imported pytest fixture
    run_db,
)


@pytest.fixture
def phase9_client(
    request: pytest.FixtureRequest,
) -> tuple[TestClient, Settings, FakeProvider]:
    return request.getfixturevalue("phase8_client")  # type: ignore[no-any-return]


def incidents_path(organization_id: str) -> str:
    return f"/api/v1/organizations/{organization_id}/incidents"


def create_manual_incident(
    client: TestClient,
    organization_id: str,
    csrf: str,
    *,
    title: str = "Investigate safe metadata",
) -> dict[str, object]:
    response = client.post(
        incidents_path(organization_id),
        headers={"X-Renzai-CSRF": csrf, "Idempotency-Key": f"manual-{title}"},
        json={"title": title, "severity": "medium", "safe_summary": "Operator report."},
    )
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


async def persisted_incidents(session: AsyncSession) -> list[Incident]:
    return list((await session.execute(select(Incident).order_by(Incident.created_at))).scalars())


@pytest.mark.parametrize(
    ("phase", "action", "status_code", "error_code", "provider_calls"),
    [
        ("input", "block", 403, "policy_block", 0),
        ("input", "require_review", 409, "review_required", 0),
        ("output", "block", 403, "policy_block", 1),
        ("output", "require_review", 409, "review_required", 1),
    ],
)
def test_gateway_escalates_contract_required_decisions(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
    phase: str,
    action: str,
    status_code: int,
    error_code: str,
    provider_calls: int,
) -> None:
    client, settings, fake = phase9_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    create_policy(client, organization_id, csrf, phase=phase, action=action)
    fake.content = "provider response that must never appear"

    response = gateway(client, key)

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == error_code
    assert fake.content not in response.text
    assert fake.calls == provider_calls
    incidents = run_db(settings, persisted_incidents)
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.status == "open"
    assert incident.action == action
    assert incident.direction == phase
    assert incident.organization_id == UUID(organization_id)
    assert incident.primary_analysis_id is not None

    detail = client.get(f"{incidents_path(organization_id)}/{incident.incident_id}")
    assert detail.status_code == 200
    assert detail.json()["analysis"]["analysis_id"] == str(incident.primary_analysis_id)
    assert detail.json()["analysis"]["state"] == "available"


def test_automatic_incident_creation_is_idempotent_and_allow_is_quiet(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, fake = phase9_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    assert gateway(client, key).status_code == 200
    assert run_db(settings, persisted_incidents) == []

    create_policy(client, organization_id, csrf, phase="input", action="block")
    assert gateway(client, key).status_code == 403
    incident = run_db(settings, persisted_incidents)[0]
    assert incident.primary_analysis_id is not None

    async def escalate_twice(session: AsyncSession) -> int:
        service = IncidentService(session)
        await service.create_from_analysis(
            UUID(organization_id),
            incident.primary_analysis_id,
            "retry-one",
        )
        await service.create_from_analysis(
            UUID(organization_id),
            incident.primary_analysis_id,
            "retry-two",
        )
        return int((await session.scalar(select(func.count()).select_from(Incident))) or 0)

    assert run_db(settings, escalate_twice) == 1
    assert fake.calls == 1


@pytest.mark.parametrize(("phase", "provider_calls"), [("input", 0), ("output", 1)])
def test_required_incident_persistence_failure_is_fail_closed(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    provider_calls: int,
) -> None:
    client, settings, fake = phase9_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    create_policy(client, organization_id, csrf, phase=phase, action="block")
    fake.content = "withheld provider response"

    async def fail_incident(*_args: object, **_kwargs: object) -> Incident:
        raise IncidentPersistenceFailure("synthetic persistence failure")

    monkeypatch.setattr(IncidentService, "create_from_analysis", fail_incident)
    response = gateway(client, key)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "inspection_failure"
    assert fake.content not in response.text
    assert fake.calls == provider_calls
    assert run_db(settings, persisted_incidents) == []

    async def outcomes(session: AsyncSession) -> list[str]:
        return list((await session.execute(select(GatewayProviderCall.outcome))).scalars())

    assert run_db(settings, outcomes) == (
        ["output_inspection_failure"] if phase == "output" else []
    )


def test_analyze_does_not_implicitly_create_incidents(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, _fake = phase9_client
    organization_id, csrf, _app, _env, key = bootstrap(client)
    create_policy(client, organization_id, csrf, phase="input", action="block")

    response = client.post(
        "/api/v1/analyze",
        headers={"Authorization": f"Bearer {key}"},
        json={"direction": "input", "content": "Routine input"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "block"
    assert run_db(settings, persisted_incidents) == []


@pytest.mark.e2e
def test_manual_queue_filter_cursor_detail_comment_and_lifecycle(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, _fake = phase9_client
    organization_id, csrf, _app, _env, _key = bootstrap(client)
    first = create_manual_incident(client, organization_id, csrf, title="First safe incident")
    replay = create_manual_incident(client, organization_id, csrf, title="First safe incident")
    assert replay["incident_id"] == first["incident_id"]
    second = create_manual_incident(client, organization_id, csrf, title="Second safe incident")

    search_match = client.get(incidents_path(organization_id), params={"search": "First"})
    assert [item["incident_id"] for item in search_match.json()["items"]] == [first["incident_id"]]
    wildcard_search = client.get(incidents_path(organization_id), params={"search": "%"})
    assert wildcard_search.json()["items"] == []

    first_page = client.get(
        incidents_path(organization_id), params={"severity": "medium", "limit": 1}
    )
    assert first_page.status_code == 200
    assert [item["title"] for item in first_page.json()["items"]] == [second["title"]]
    cursor = first_page.json()["next_cursor"]
    assert cursor
    next_page = client.get(
        incidents_path(organization_id),
        params={"severity": "medium", "limit": 1, "cursor": cursor},
    )
    assert [item["title"] for item in next_page.json()["items"]] == [first["title"]]
    assert (
        client.get(
            incidents_path(organization_id),
            params={"status": "resolved", "cursor": cursor},
        ).status_code
        == 422
    )

    incident_id = str(first["incident_id"])
    comment_text = '<script>alert("stored-xss")</script> is plain text'
    comment = client.post(
        f"{incidents_path(organization_id)}/{incident_id}/comments",
        headers={"X-Renzai-CSRF": csrf},
        json={"body": comment_text},
    )
    assert comment.status_code == 201
    detail = client.get(f"{incidents_path(organization_id)}/{incident_id}").json()
    assert detail["comments"][0]["body"] == comment_text
    assert detail["timeline"][-1]["event_type"] == "comment_added"
    assert comment_text not in str(detail["timeline"])

    transition = client.patch(
        f"{incidents_path(organization_id)}/{incident_id}/status",
        headers={"X-Renzai-CSRF": csrf},
        json={"status": "false_positive", "version": detail["version"], "reason": "Reviewed"},
    )
    assert transition.status_code == 200
    assert transition.json()["status"] == "false_positive"
    assert transition.json()["timeline"][-1]["event_type"] == "false_positive_marked"
    stale = client.patch(
        f"{incidents_path(organization_id)}/{incident_id}/status",
        headers={"X-Renzai-CSRF": csrf},
        json={"status": "investigating", "version": detail["version"], "reason": "Reopen"},
    )
    assert stale.status_code == 409
    no_reason = client.patch(
        f"{incidents_path(organization_id)}/{incident_id}/status",
        headers={"X-Renzai-CSRF": csrf},
        json={
            "status": "investigating",
            "version": transition.json()["version"],
            "reason": None,
        },
    )
    assert no_reason.status_code == 409
    assert no_reason.json()["error"]["code"] == "invalid_transition"

    async def audit_content(session: AsyncSession) -> tuple[int, int, bool]:
        comments = int(
            (await session.scalar(select(func.count()).select_from(IncidentComment))) or 0
        )
        timeline = int(
            (await session.scalar(select(func.count()).select_from(IncidentTimelineEvent))) or 0
        )
        return comments, timeline, comment_text in str(session.info)

    assert run_db(settings, audit_content) == (1, 4, False)


def test_manual_incident_metadata_redacts_detectable_credentials(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, _settings, _fake = phase9_client
    organization_id, csrf, _app, _env, _key = bootstrap(client)
    credential = "sk_abcdefghijklmnopqrstuvwx"  # noqa: S105 - synthetic detector fixture
    response = client.post(
        incidents_path(organization_id),
        headers={"X-Renzai-CSRF": csrf},
        json={
            "title": f"Credential {credential} reported",
            "severity": "high",
            "safe_summary": f"Operator found {credential}",
        },
    )
    assert response.status_code == 201
    assert credential not in response.text
    assert "[REDACTED:API_KEY]" in response.text


@pytest.mark.parametrize(
    ("current", "target", "allowed", "reason"),
    [
        ("open", "investigating", True, None),
        ("open", "resolved", True, None),
        ("open", "ignored", True, None),
        ("open", "false_positive", True, None),
        ("investigating", "open", True, None),
        ("investigating", "resolved", True, None),
        ("investigating", "ignored", True, None),
        ("investigating", "false_positive", True, None),
        ("resolved", "investigating", True, "New evidence"),
        ("ignored", "investigating", True, "New evidence"),
        ("false_positive", "investigating", True, "New evidence"),
        ("resolved", "open", False, "No direct reopen"),
        ("false_positive", "open", False, "No direct reopen"),
        ("open", "open", False, None),
        ("resolved", "investigating", False, None),
    ],
)
def test_all_status_transition_rules(
    current: str, target: str, allowed: bool, reason: str | None
) -> None:
    if allowed:
        validate_transition(IncidentStatus(current), IncidentStatus(target), reason)
    else:
        with pytest.raises(InvalidIncidentTransition):
            validate_transition(IncidentStatus(current), IncidentStatus(target), reason)


@pytest.mark.parametrize(
    ("role", "can_edit", "can_comment"),
    [
        ("owner", True, True),
        ("admin", True, True),
        ("security_analyst", True, True),
        ("developer", False, True),
        ("viewer", False, False),
    ],
)
@pytest.mark.e2e
def test_incident_rbac_matrix(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
    role: str,
    can_edit: bool,
    can_comment: bool,
) -> None:
    client, settings, _fake = phase9_client
    organization_id, csrf, _app, _env, _key = bootstrap(client)
    incident = create_manual_incident(client, organization_id, csrf)

    async def set_role(session: AsyncSession) -> UUID:
        membership = (
            await session.execute(
                select(Membership).where(Membership.organization_id == UUID(organization_id))
            )
        ).scalar_one()
        membership.role = role
        return membership.user_id

    user_id = run_db(settings, set_role)
    assert client.get(incidents_path(organization_id)).status_code == 200
    assert (
        client.get(f"{incidents_path(organization_id)}/{incident['incident_id']}").status_code
        == 200
    )

    assignment = client.patch(
        f"{incidents_path(organization_id)}/{incident['incident_id']}/assignment",
        headers={"X-Renzai-CSRF": csrf},
        json={"assignee_user_id": str(user_id), "version": incident["version"]},
    )
    assert assignment.status_code == (200 if can_edit else 403)
    version = assignment.json()["version"] if can_edit else incident["version"]
    status_change = client.patch(
        f"{incidents_path(organization_id)}/{incident['incident_id']}/status",
        headers={"X-Renzai-CSRF": csrf},
        json={"status": "investigating", "version": version, "reason": None},
    )
    assert status_change.status_code == (200 if can_edit else 403)
    comment = client.post(
        f"{incidents_path(organization_id)}/{incident['incident_id']}/comments",
        headers={"X-Renzai-CSRF": csrf},
        json={"body": "Bounded plain-text comment"},
    )
    assert comment.status_code == (201 if can_comment else 403)


def test_false_positive_preserves_analysis_and_retention_keeps_incident(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, _fake = phase9_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    create_policy(client, organization_id, csrf, phase="input", action="block")
    assert gateway(client, key).status_code == 403
    incident = run_db(settings, persisted_incidents)[0]

    async def snapshot(session: AsyncSession) -> tuple[int, int, int, int | None]:
        analysis_id = incident.primary_analysis_id
        result = await session.get(AnalysisResult, analysis_id)
        assert result is not None
        return (
            int((await session.scalar(select(func.count()).select_from(Finding))) or 0),
            int((await session.scalar(select(func.count()).select_from(RiskContribution))) or 0),
            int((await session.scalar(select(func.count()).select_from(PolicyDecision))) or 0),
            result.risk_score,
        )

    before = run_db(settings, snapshot)
    response = client.patch(
        f"{incidents_path(organization_id)}/{incident.incident_id}/status",
        headers={"X-Renzai-CSRF": csrf},
        json={"status": "false_positive", "version": 1, "reason": "Human classification"},
    )
    assert response.status_code == 200
    assert run_db(settings, snapshot) == before

    async def expire_event(session: AsyncSession) -> tuple[int, int]:
        # SQLite test connections do not enable FK actions; model the PostgreSQL
        # ON DELETE CASCADE that removes only the relation, never the incident.
        await session.execute(
            delete(IncidentSecurityEvent).where(
                IncidentSecurityEvent.event_id == incident.primary_event_id
            )
        )
        await session.execute(
            delete(SecurityEvent).where(SecurityEvent.event_id == incident.primary_event_id)
        )
        incidents = int((await session.scalar(select(func.count()).select_from(Incident))) or 0)
        relations = int(
            (await session.scalar(select(func.count()).select_from(IncidentSecurityEvent))) or 0
        )
        return incidents, relations

    assert run_db(settings, expire_event) == (1, 0)
    detail = client.get(f"{incidents_path(organization_id)}/{incident.incident_id}")
    assert detail.status_code == 200
    assert detail.json()["analysis"] == {"state": "content_no_longer_retained"}


def test_tenant_isolation_and_assignee_membership_validation(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, _fake = phase9_client
    organization_id, csrf, _app, _env, _key = bootstrap(client)
    incident = create_manual_incident(client, organization_id, csrf)
    second = client.post(
        "/api/v1/organizations",
        headers={"X-Renzai-CSRF": csrf},
        json={"name": "Other Tenant", "slug": "phase-nine-other"},
    )
    assert second.status_code == 201
    other_organization_id = second.json()["organization_id"]
    foreign_user_id = new_uuid7()
    inactive_user_id = new_uuid7()

    async def seed_memberships(session: AsyncSession) -> None:
        session.add_all(
            [
                User(
                    user_id=foreign_user_id,
                    email=f"{foreign_user_id}@example.test",
                    normalized_email=f"{foreign_user_id}@example.test",
                ),
                User(
                    user_id=inactive_user_id,
                    email=f"{inactive_user_id}@example.test",
                    normalized_email=f"{inactive_user_id}@example.test",
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                Membership(
                    organization_id=UUID(other_organization_id),
                    user_id=foreign_user_id,
                    role="security_analyst",
                    status="active",
                ),
                Membership(
                    organization_id=UUID(organization_id),
                    user_id=inactive_user_id,
                    role="security_analyst",
                    status="removed",
                ),
            ]
        )

    run_db(settings, seed_memberships)
    incident_id = str(incident["incident_id"])
    assert client.get(f"{incidents_path(other_organization_id)}/{incident_id}").status_code == 404
    assert client.get(incidents_path(other_organization_id)).json()["items"] == []
    for suffix, method, payload in (
        ("status", client.patch, {"status": "investigating", "version": 1, "reason": None}),
        (
            "assignment",
            client.patch,
            {"assignee_user_id": str(foreign_user_id), "version": 1},
        ),
        ("comments", client.post, {"body": "Foreign tenant attempt"}),
    ):
        response = method(
            f"{incidents_path(other_organization_id)}/{incident_id}/{suffix}",
            headers={"X-Renzai-CSRF": csrf},
            json=payload,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found_or_hidden"

    for assignee_id in (foreign_user_id, inactive_user_id):
        response = client.patch(
            f"{incidents_path(organization_id)}/{incident_id}/assignment",
            headers={"X-Renzai-CSRF": csrf},
            json={"assignee_user_id": str(assignee_id), "version": 1},
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found_or_hidden"


def test_incident_detail_obeys_full_redacted_and_metadata_privacy(
    phase9_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, _fake = phase9_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    policy = client.post(
        f"/api/v1/organizations/{organization_id}/policies",
        headers={"X-Renzai-CSRF": csrf},
        json={
            "name": "Block every input for privacy verification",
            "scope_kind": "organization",
            "scope_id": organization_id,
            "phase": "input",
            "priority": 4,
            "enabled": True,
            "action": "block",
            "rationale_code": "phase9_privacy_block",
            "condition_mode": "all",
            "conditions": [{"field": "risk_score", "operator": "greater_or_equal", "value": 0}],
            "redaction_targets": [],
        },
    )
    assert policy.status_code == 201, policy.text
    app_path = f"/api/v1/organizations/{organization_id}/applications/{app['application_id']}"
    assert (
        client.patch(
            app_path,
            headers={"X-Renzai-CSRF": csrf},
            json={"privacy_mode": "FULL", "safe_content_persistence": True},
        ).status_code
        == 200
    )
    full_content = "Routine full-mode incident content"
    assert (
        gateway(client, key, messages=[{"role": "user", "content": full_content}]).status_code
        == 403
    )
    full_incident = run_db(settings, persisted_incidents)[-1]
    full_detail = client.get(
        f"{incidents_path(organization_id)}/{full_incident.incident_id}"
    ).json()
    assert full_content in full_detail["analysis"]["content"]

    assert (
        client.patch(
            app_path,
            headers={"X-Renzai-CSRF": csrf},
            json={"privacy_mode": "REDACTED", "safe_content_persistence": False},
        ).status_code
        == 200
    )
    secret = "Bearer abcdefghijklmnopqrstuvwxyz123456"  # noqa: S105 - synthetic detector input
    assert gateway(client, key, messages=[{"role": "user", "content": secret}]).status_code == 403
    redacted_incident = run_db(settings, persisted_incidents)[-1]
    redacted_detail = client.get(
        f"{incidents_path(organization_id)}/{redacted_incident.incident_id}"
    )
    assert secret not in redacted_detail.text
    assert "[REDACTED:" in redacted_detail.text

    assert (
        client.patch(
            app_path,
            headers={"X-Renzai-CSRF": csrf},
            json={"privacy_mode": "METADATA_ONLY"},
        ).status_code
        == 200
    )
    assert gateway(client, key).status_code == 403
    metadata_incident = run_db(settings, persisted_incidents)[-1]
    metadata_detail = client.get(
        f"{incidents_path(organization_id)}/{metadata_incident.incident_id}"
    ).json()
    assert "content" not in metadata_detail["analysis"]
    assert metadata_detail["analysis"]["content_state"] == "not_retained"
