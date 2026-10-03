from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from renzai.api.analyze import AnalyzeRequest
from renzai.app import create_app
from renzai.core.config import Environment, Settings
from renzai.db import models as _models  # noqa: F401
from renzai.db.base import Base
from renzai.db.session import Database
from renzai.infrastructure.crypto.ai_credentials import AICredentialKeyRing
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.infrastructure.http.ai_openai_compatible import (
    AIProviderRuntimeConfig,
    OpenAICompatibleAIIntelligenceProvider,
)
from renzai.modules.ai_intelligence.domain import AIProviderFailure, AITaskType


@pytest.fixture
def security_client(tmp_path: Path) -> Iterator[TestClient]:
    database_path = tmp_path / "phase13.sqlite3"
    settings = Settings(
        app_environment=Environment.TEST,
        app_public_base_url="http://testserver",
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        session_secure_cookie=False,
        auth_rate_limit_attempts=100,
    )

    async def create_schema() -> None:
        database = Database(settings.database)
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await database.close()

    asyncio.run(create_schema())
    with TestClient(create_app(settings), base_url="http://testserver") as client:
        yield client


def _register(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "security@example.com", "password": "correct horse 12345"},
    )
    assert response.status_code == 201, response.text


def _csrf(client: TestClient) -> str:
    response = client.get("/api/v1/auth/session")
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def test_login_rotates_a_presented_live_session(security_client: TestClient) -> None:
    _register(security_client)
    old_cookie = security_client.cookies.get("renzai_session")
    assert old_cookie

    login = security_client.post(
        "/api/v1/auth/login",
        json={"email": "security@example.com", "password": "correct horse 12345"},
    )
    assert login.status_code == 200, login.text
    new_cookie = security_client.cookies.get("renzai_session")
    assert new_cookie and new_cookie != old_cookie

    security_client.cookies.clear()
    security_client.cookies.set("renzai_session", old_cookie)
    assert security_client.get("/api/v1/auth/session").status_code == 401

    security_client.cookies.clear()
    security_client.cookies.set("renzai_session", new_cookie)
    assert security_client.get("/api/v1/auth/session").status_code == 200


def test_security_sensitive_request_models_reject_unknown_fields(
    security_client: TestClient,
) -> None:
    registration = security_client.post(
        "/api/v1/auth/register",
        json={
            "email": "unknown-field@example.com",
            "password": "correct horse 12345",
            "is_admin": True,
        },
    )
    assert registration.status_code == 422

    _register(security_client)
    organization = security_client.post(
        "/api/v1/organizations",
        headers={"X-Renzai-CSRF": _csrf(security_client)},
        json={"name": "Security", "slug": "security-org", "owner_override": True},
    )
    assert organization.status_code == 422


def test_analyze_rejects_unknown_fields_and_malformed_origin_is_safe(
    security_client: TestClient,
) -> None:
    with pytest.raises(PydanticValidationError):
        AnalyzeRequest.model_validate(
            {"content": "safe", "direction": "input", "admin_override": True}
        )

    malformed = security_client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://["},
        json={"email": "security@example.com", "password": "correct horse 12345"},
    )
    assert malformed.status_code == 403
    assert malformed.json()["error"]["code"] == "authorization"


def test_sensitive_api_responses_are_non_cacheable_and_non_renderable(
    security_client: TestClient,
) -> None:
    response = security_client.get("/api/v1/auth/session")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )


def test_opaque_credentials_reject_oversized_or_malformed_values_before_lookup() -> None:
    crypto = IdentityCrypto("phase13-identity-root-material-000001", "v1")
    assert crypto.lookup(f"{'A' * 10_000}.{'B' * 43}") is None
    assert crypto.lookup("A" * 22 + "." + "B" * 42) is None
    assert crypto.lookup("A" * 22 + "." + "B" * 43) == "A" * 22


def test_password_hash_records_the_explicit_argon2id_cost_profile() -> None:
    crypto = IdentityCrypto("phase13-identity-root-material-000001", "v1")
    encoded = crypto.hash_password("correct horse 12345")
    assert encoded.startswith("$argon2id$v=19$m=65536,t=3,p=4$")


def test_general_json_body_limit_rejects_before_model_processing(tmp_path: Path) -> None:
    settings = Settings(
        app_environment=Environment.TEST,
        app_public_base_url="http://testserver",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'body.sqlite3').as_posix()}",
        session_secure_cookie=False,
        app_max_json_body_bytes=1024,
    )
    with TestClient(create_app(settings), base_url="http://testserver") as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "security@example.com",
                "password": "correct horse 12345",
                "padding": "A" * 2048,
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["details"] == {"fields": ["body"]}


def test_cookie_authenticated_writes_use_fail_closed_session_rate_limit(tmp_path: Path) -> None:
    database_path = tmp_path / "session-limit.sqlite3"
    settings = Settings(
        app_environment=Environment.TEST,
        app_public_base_url="http://testserver",
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        session_secure_cookie=False,
        auth_rate_limit_attempts=100,
        session_rate_limit_requests=1,
        session_rate_limit_window_seconds=60,
    )

    async def create_schema() -> None:
        database = Database(settings.database)
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await database.close()

    asyncio.run(create_schema())
    with TestClient(create_app(settings), base_url="http://testserver") as client:
        _register(client)
        token = _csrf(client)
        first = client.post(
            "/api/v1/organizations",
            headers={"X-Renzai-CSRF": token},
            json={"name": "First Organization", "slug": "first-organization"},
        )
        second = client.post(
            "/api/v1/organizations",
            headers={"X-Renzai-CSRF": token},
            json={"name": "Second Organization", "slug": "second-organization"},
        )
    assert first.status_code == 201
    assert second.status_code == 429


class _NestedResponseClient:
    async def request(self, **_: object) -> tuple[int, bytes]:
        return 200, b"[" * 1100 + b"0" + b"]" * 1100


async def test_maliciously_nested_ai_provider_json_is_normalized_to_safe_failure() -> None:
    provider = OpenAICompatibleAIIntelligenceProvider(
        _NestedResponseClient(),  # type: ignore[arg-type]
        AICredentialKeyRing("v1", {"v1": "phase13-ai-root-material-0000000001"}),
    )
    config = AIProviderRuntimeConfig(
        config_id=UUID("71000000-0000-7000-8000-000000000031"),
        organization_id=UUID("71000000-0000-7000-8000-000000000032"),
        kind="openai_compatible_local",
        base_url="http://127.0.0.1:11434",
        model="safe-model",
        credential_ciphertext=None,
        credential_key_id=None,
        connect_timeout_seconds=1,
        request_timeout_seconds=1,
        response_max_bytes=128 * 1024,
    )
    with pytest.raises(AIProviderFailure, match="AI provider request failed"):
        await provider.generate(
            config=config,
            task_type=AITaskType.INCIDENT_SUMMARY,
            context={"incident": {"incident_id": "synthetic"}},
        )
