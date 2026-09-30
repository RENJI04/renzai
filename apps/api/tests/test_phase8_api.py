from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from renzai.app import create_app
from renzai.core.config import Environment as RuntimeEnvironment
from renzai.core.config import Settings
from renzai.db import models as _models  # noqa: F401
from renzai.db.base import Base
from renzai.db.session import Database
from renzai.modules.audit.models import AuditEvent
from renzai.modules.gateway.models import GatewayProviderCall
from renzai.modules.memberships.models import Membership
from renzai.modules.policies.models import PolicyDecision
from renzai.modules.providers.domain import (
    ProviderChatRequest,
    ProviderCompletion,
    ProviderConfigurationFailure,
    ProviderFailure,
    ProviderRuntimeConfig,
    ProviderTimeout,
)
from renzai.modules.providers.models import ProviderConfiguration
from renzai.modules.security.application import AnalysisService
from renzai.modules.security.domain.types import Direction, InspectionFailure
from renzai.modules.security.models import AnalysisResult, SecurityEvent


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.health_calls = 0
        self.last_request: ProviderChatRequest | None = None
        self.content = "A safe provider answer."
        self.failure: str | None = None

    async def complete(
        self, request: ProviderChatRequest, config: ProviderRuntimeConfig
    ) -> ProviderCompletion:
        self.calls += 1
        self.last_request = request
        if self.failure == "timeout":
            raise ProviderTimeout("synthetic timeout")
        if self.failure == "error":
            raise ProviderFailure("synthetic upstream body that must stay hidden")
        if self.failure == "config":
            raise ProviderConfigurationFailure("synthetic credential failure")
        return ProviderCompletion(
            completion_id="chatcmpl-phase8",
            created=1,
            model=config.model,
            content=self.content,
            finish_reason="stop",
            usage={"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        )

    async def check_health(self, config: ProviderRuntimeConfig) -> None:
        self.health_calls += 1


@pytest.fixture
def phase8_client(tmp_path: Path) -> Iterator[tuple[TestClient, Settings, FakeProvider]]:
    database_path = tmp_path / "phase8.sqlite3"
    settings = Settings(
        app_environment=RuntimeEnvironment.TEST,
        app_public_base_url="http://testserver",
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        session_secure_cookie=False,
        auth_rate_limit_attempts=100,
        analyze_rate_limit_requests=100,
        gateway_rate_limit_requests=100,
        outbound_trusted_local_provider_hosts=("127.0.0.1",),
    )

    async def create_schema() -> None:
        database = Database(settings.database)
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await database.close()

    asyncio.run(create_schema())
    fake = FakeProvider()
    with TestClient(create_app(settings), base_url="http://testserver") as client:
        client.app.state.dependencies.chat_provider = fake
        yield client, settings, fake


def run_db[T](settings: Settings, operation: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async def execute() -> T:
        database = Database(settings.database)
        async with database.session() as session:
            result = await operation(session)
            await session.commit()
        await database.close()
        return result

    return asyncio.run(execute())


def bootstrap(client: TestClient) -> tuple[str, str, dict[str, object], dict[str, object], str]:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "phase8@example.com", "password": "correct horse 12345"},
    )
    assert registered.status_code == 201, registered.text
    csrf = client.get("/api/v1/auth/session").json()["csrf_token"]
    organization = client.post(
        "/api/v1/organizations",
        headers={"X-Renzai-CSRF": csrf},
        json={"name": "Phase Eight", "slug": "phase-eight"},
    )
    assert organization.status_code == 201, organization.text
    organization_id = organization.json()["organization_id"]
    application = client.post(
        f"/api/v1/organizations/{organization_id}/applications",
        headers={"X-Renzai-CSRF": csrf},
        json={"name": "Gateway"},
    )
    assert application.status_code == 201, application.text
    app = application.json()
    environment = client.post(
        f"/api/v1/organizations/{organization_id}/applications/{app['application_id']}"
        "/environments",
        headers={"X-Renzai-CSRF": csrf},
        json={"type": "development"},
    )
    assert environment.status_code == 201, environment.text
    env = environment.json()
    key = client.post(
        f"/api/v1/organizations/{organization_id}/applications/{app['application_id']}"
        f"/environments/{env['environment_id']}/keys",
        headers={"X-Renzai-CSRF": csrf},
        json={"label": "gateway"},
    )
    assert key.status_code == 201, key.text
    return organization_id, csrf, app, env, key.json()["secret_once"]


def providers_path(organization_id: str, app: dict[str, object], env: dict[str, object]) -> str:
    return (
        f"/api/v1/organizations/{organization_id}/applications/{app['application_id']}"
        f"/environments/{env['environment_id']}/providers"
    )


def create_provider(
    client: TestClient,
    organization_id: str,
    csrf: str,
    app: dict[str, object],
    env: dict[str, object],
    *,
    credential: str = "provider-secret-value",
) -> dict[str, object]:
    response = client.post(
        providers_path(organization_id, app, env),
        headers={"X-Renzai-CSRF": csrf},
        json={
            "kind": "openai_compatible_local",
            "name": "Local deterministic mock",
            "base_url": "http://127.0.0.1:11434/v1/",
            "model": "safe-model",
            "credential": credential,
            "supports_seed": True,
            "max_tokens": 1024,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def gateway(client: TestClient, key: str, **overrides: object):
    body: dict[str, object] = {
        "model": "safe-model",
        "messages": [{"role": "user", "content": "Hello provider"}],
        "stream": False,
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 100,
        "stop": ["DONE"],
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "seed": 7,
    }
    body.update(overrides)
    return client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json=body,
    )


def create_policy(
    client: TestClient,
    organization_id: str,
    csrf: str,
    *,
    phase: str,
    action: str,
    redaction_targets: list[str] | None = None,
) -> None:
    response = client.post(
        f"/api/v1/organizations/{organization_id}/policies",
        headers={"X-Renzai-CSRF": csrf},
        json={
            "name": f"Gateway {phase} {action}",
            "scope_kind": "organization",
            "scope_id": organization_id,
            "phase": phase,
            "priority": 5,
            "enabled": True,
            "action": action,
            "rationale_code": f"gateway_{phase}_{action}",
            "condition_mode": "all",
            "conditions": [{"field": "severity", "operator": "equals", "value": "low"}],
            "redaction_targets": redaction_targets or [],
        },
    )
    assert response.status_code == 201, response.text


async def persisted_gateway_decisions(
    session: AsyncSession,
) -> list[tuple[str, str | None, int | None, str]]:
    rows = (
        await session.execute(
            select(SecurityEvent, AnalysisResult, PolicyDecision)
            .join(AnalysisResult, AnalysisResult.event_id == SecurityEvent.event_id)
            .join(PolicyDecision, PolicyDecision.analysis_id == AnalysisResult.analysis_id)
            .where(SecurityEvent.source == "gateway")
            .order_by(SecurityEvent.occurred_at, SecurityEvent.event_id)
        )
    ).all()
    return [
        (event.direction, event.action, result.risk_score, decision.action)
        for event, result, decision in rows
    ]


def test_provider_management_encrypts_masks_validates_and_audits(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, fake = phase8_client
    organization_id, csrf, app, env, _key = bootstrap(client)
    secret = "provider-secret-value"  # noqa: S105 - synthetic credential fixture
    created = create_provider(client, organization_id, csrf, app, env, credential=secret)
    assert created["credential_present"] is True
    assert secret not in str(created)
    assert created["base_url"] == "http://127.0.0.1:11434/v1"
    path = providers_path(organization_id, app, env)
    assert client.get(path).json()["items"][0]["provider_id"] == created["provider_id"]
    validated = client.post(
        f"{path}/{created['provider_id']}/validate", headers={"X-Renzai-CSRF": csrf}
    )
    assert validated.status_code == 200
    assert validated.json()["last_validation_status"] == "success"
    assert fake.health_calls == 1

    async def persisted(session: AsyncSession) -> tuple[bytes, list[AuditEvent]]:
        provider = (await session.execute(select(ProviderConfiguration))).scalar_one()
        audits = list(
            (
                await session.execute(
                    select(AuditEvent).where(AuditEvent.resource_type == "provider_configuration")
                )
            ).scalars()
        )
        assert provider.credential_ciphertext is not None
        return provider.credential_ciphertext, audits

    ciphertext, audits = run_db(settings, persisted)
    assert secret.encode() not in ciphertext
    assert {event.action for event in audits} == {"provider.created", "provider.validated"}
    assert secret not in str([event.safe_metadata for event in audits])

    async def demote(session: AsyncSession) -> None:
        await session.execute(
            update(Membership)
            .where(Membership.organization_id == UUID(organization_id))
            .values(role="security_analyst")
        )

    run_db(settings, demote)
    denied = client.post(
        f"{path}/{created['provider_id']}/disable", headers={"X-Renzai-CSRF": csrf}
    )
    assert denied.status_code == 403


def test_provider_api_normalizes_unsafe_target_as_validation_error(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, _settings, fake = phase8_client
    organization_id, csrf, app, env, _key = bootstrap(client)
    response = client.post(
        providers_path(organization_id, app, env),
        headers={"X-Renzai-CSRF": csrf},
        json={
            "kind": "openai_compatible_remote",
            "name": "Unsafe remote",
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "safe-model",
            "credential": "provider-secret-value",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"] == {"fields": ["base_url"]}
    assert fake.calls == 0


def test_gateway_sanitizes_forwards_inspects_redacts_and_persists(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    fake.content = "Bearer abcdefghijklmnopqrstuvwxyz123456"
    response = gateway(client, key)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"].startswith("[REDACTED:")
    assert fake.content not in response.text
    assert response.headers["X-Renzai-Input-Action"] == "allow"
    assert response.headers["X-Renzai-Output-Action"] == "redact"
    assert fake.calls == 1
    assert fake.last_request is not None
    assert fake.last_request.as_payload() == {
        "model": "safe-model",
        "messages": [{"role": "user", "content": "Hello provider"}],
        "stream": False,
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 100,
        "stop": ["DONE"],
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "seed": 7,
    }

    async def persisted(session: AsyncSession) -> tuple[list[SecurityEvent], GatewayProviderCall]:
        events = list(
            (
                await session.execute(
                    select(SecurityEvent)
                    .where(SecurityEvent.source == "gateway")
                    .order_by(SecurityEvent.occurred_at)
                )
            ).scalars()
        )
        call = (await session.execute(select(GatewayProviderCall))).scalar_one()
        return events, call

    events, call = run_db(settings, persisted)
    assert [event.direction for event in events] == ["input", "output"]
    assert [event.action for event in events] == ["allow", "redact"]
    assert call.input_analysis_id is not None and call.output_analysis_id is not None
    assert call.outcome == "completed"


@pytest.mark.parametrize(
    ("action", "status_code", "code"),
    [("block", 403, "policy_block"), ("require_review", 409, "review_required")],
)
def test_gateway_input_withholding_never_contacts_provider(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
    action: str,
    status_code: int,
    code: str,
) -> None:
    client, settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    create_policy(client, organization_id, csrf, phase="input", action=action)
    response = gateway(client, key)
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == {"phase": "input"}
    assert fake.calls == 0
    assert run_db(settings, persisted_gateway_decisions) == [("input", action, 0, action)]


def test_gateway_provider_selection_failure_preserves_input_decision(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, fake = phase8_client
    _organization_id, _csrf, _app, _env, key = bootstrap(client)

    response = gateway(client, key)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "configuration_error"
    assert fake.calls == 0
    assert run_db(settings, persisted_gateway_decisions) == [("input", "allow", 0, "allow")]


@pytest.mark.parametrize(
    ("failure", "status_code", "code"),
    [
        ("timeout", 504, "provider_timeout"),
        ("error", 502, "provider_error"),
        ("config", 503, "configuration_error"),
    ],
)
def test_gateway_provider_failures_are_safe_and_not_retried(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
    failure: str,
    status_code: int,
    code: str,
) -> None:
    client, _settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    fake.failure = failure
    response = gateway(client, key)
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
    assert "synthetic" not in response.text
    assert fake.calls == 1


@pytest.mark.parametrize(
    ("action", "status_code", "code"),
    [("block", 403, "policy_block"), ("require_review", 409, "review_required")],
)
def test_gateway_output_withholds_provider_content(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
    action: str,
    status_code: int,
    code: str,
) -> None:
    client, _settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    create_policy(client, organization_id, csrf, phase="output", action=action)
    fake.content = "private provider answer that must be withheld"
    response = gateway(client, key)
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == {"phase": "output"}
    assert fake.content not in response.text
    assert fake.calls == 1


def test_gateway_input_redaction_failure_preserves_decision_without_provider_call(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    create_policy(
        client,
        organization_id,
        csrf,
        phase="input",
        action="redact",
        redaction_targets=["secret_exposure"],
    )
    input_failure = gateway(client, key)
    assert input_failure.status_code == 503
    assert input_failure.json()["error"]["code"] == "inspection_failure"
    assert fake.calls == 0
    assert run_db(settings, persisted_gateway_decisions) == [("input", "redact", 0, "redact")]


def test_gateway_output_redaction_failure_is_truthfully_persisted(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    create_policy(
        client,
        organization_id,
        csrf,
        phase="output",
        action="redact",
        redaction_targets=["secret_exposure"],
    )
    fake.content = "Bearer abcdefghijklmnopqrstuvwxyz123456"
    original = AnalysisService.analyze

    async def invalidate_output_redaction(
        self: AnalysisService, *args: object, **kwargs: object
    ) -> dict[str, object]:
        result = await original(self, *args, **kwargs)  # type: ignore[arg-type]
        if args[3] is Direction.OUTPUT:
            result["redacted_content"] = ""
        return result

    monkeypatch.setattr(AnalysisService, "analyze", invalidate_output_redaction)
    output_failure = gateway(client, key)
    assert output_failure.status_code == 503
    assert output_failure.json()["error"]["code"] == "inspection_failure"
    assert fake.content not in output_failure.text
    assert fake.calls == 1

    decisions = run_db(settings, persisted_gateway_decisions)
    assert [(direction, action) for direction, action, _risk, _policy in decisions] == [
        ("input", "allow"),
        ("output", "redact"),
    ]

    async def persisted_call(session: AsyncSession) -> GatewayProviderCall:
        return (await session.execute(select(GatewayProviderCall))).scalar_one()

    call = run_db(settings, persisted_call)
    assert call.output_analysis_id is not None
    assert call.outcome == "output_inspection_failure"
    assert call.outcome != "completed"


def test_gateway_inspection_failures_are_fail_closed(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)

    async def input_failure(*args: object, **kwargs: object) -> dict[str, object]:
        raise InspectionFailure("synthetic input detector failure")

    monkeypatch.setattr(AnalysisService, "analyze", input_failure)
    failed_input = gateway(client, key)
    assert failed_input.status_code == 503
    assert fake.calls == 0

    monkeypatch.undo()
    original = AnalysisService.analyze
    calls = 0

    async def output_failure(
        self: AnalysisService, *args: object, **kwargs: object
    ) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise InspectionFailure("synthetic output policy failure")
        return await original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(AnalysisService, "analyze", output_failure)
    fake.content = "provider output must remain withheld"
    failed_output = gateway(client, key)
    assert failed_output.status_code == 503
    assert fake.content not in failed_output.text
    assert fake.calls == 1


def test_gateway_input_persistence_failure_is_fail_closed(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)

    async def persistence_failure(*args: object, **kwargs: object) -> dict[str, object]:
        raise SQLAlchemyError("synthetic input persistence failure")

    monkeypatch.setattr(AnalysisService, "analyze", persistence_failure)
    response = gateway(client, key)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "inspection_failure"
    assert fake.calls == 0


@pytest.mark.parametrize(
    "field",
    ["tools", "functions", "response_format", "max_completion_tokens", "unknown_field"],
)
def test_gateway_rejects_unsupported_fields_before_provider(
    phase8_client: tuple[TestClient, Settings, FakeProvider], field: str
) -> None:
    client, _settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    response = gateway(client, key, **{field: {}})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation"
    assert fake.calls == 0


def test_gateway_rejects_stream_model_escape_and_provider_limits(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, _settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    assert gateway(client, key, stream=True).status_code == 422
    assert gateway(client, key, model="other-model").status_code == 422
    assert gateway(client, key, max_tokens=1025).status_code == 422
    assert fake.calls == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"temperature": -0.01},
        {"temperature": 2.01},
        {"top_p": 0},
        {"top_p": 1.01},
        {"presence_penalty": -2.01},
        {"frequency_penalty": 2.01},
        {"seed": -(2**31) - 1},
        {"seed": 2**31},
        {"stop": []},
        {"stop": ["a", "b", "c", "d", "e"]},
        {"stop": [""]},
        {"messages": [{"role": "tool", "content": "not supported"}]},
        {"messages": [{"role": "user", "content": [{"type": "text", "text": "no"}]}]},
        {"messages": [{"role": "user", "content": "x"}] * 33},
        {"messages": [{"role": "user", "content": "x" * (64 * 1024 + 1)}]},
    ],
)
def test_gateway_rejects_parameter_and_message_bounds_before_provider(
    phase8_client: tuple[TestClient, Settings, FakeProvider], overrides: dict[str, object]
) -> None:
    client, _settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    response = gateway(client, key, **overrides)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation"
    assert fake.calls == 0


def test_gateway_rejects_seed_when_provider_does_not_support_it(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    provider = create_provider(client, organization_id, csrf, app, env)

    async def disable_seed(session: AsyncSession) -> None:
        await session.execute(
            update(ProviderConfiguration)
            .where(ProviderConfiguration.provider_id == UUID(str(provider["provider_id"])))
            .values(supports_seed=False)
        )

    run_db(settings, disable_seed)
    response = gateway(client, key, seed=1)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation"
    assert fake.calls == 0


def test_gateway_rejects_oversized_body_before_provider(
    phase8_client: tuple[TestClient, Settings, FakeProvider],
) -> None:
    client, settings, fake = phase8_client
    organization_id, csrf, app, env, key = bootstrap(client)
    create_provider(client, organization_id, csrf, app, env)
    response = gateway(client, key, unknown_field="x" * settings.gateway.max_body_bytes)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation"
    assert response.json()["error"]["details"] == {"fields": ["body"]}
    assert fake.calls == 0
