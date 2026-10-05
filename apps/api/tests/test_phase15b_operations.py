from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from types import ModuleType
from urllib.error import HTTPError

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace.status import Status, StatusCode

from renzai.infrastructure.observability.telemetry import SafeSpanExporter

ROOT = Path(__file__).parents[3]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deployment_configuration_rejects_placeholders_and_insecure_public_url() -> None:
    validator = _load_script("validate_deployment_env")
    errors = validator.validate(
        {
            "POSTGRES_PASSWORD": "replace-me",
            "RENZAI_DATABASE_URL": "postgresql+asyncpg://renzai:replace-me@postgres/renzai",
            "RENZAI_APP_PUBLIC_BASE_URL": "http://example.test",
            "RENZAI_SESSION_SECURE_COOKIE": "false",
            "RENZAI_LOGGING_JSON": "false",
            "RENZAI_SESSION_VERIFIER_KEY": "replace-me",
            "RENZAI_APPLICATION_KEY_VERIFIER_KEY": "replace-me",
            "RENZAI_PROVIDER_CREDENTIAL_KEYS": "replace-me",
            "GF_SECURITY_ADMIN_PASSWORD": "replace-me",
        }
    )
    assert len(errors) == 9


def test_deployment_configuration_accepts_separated_runtime_secrets() -> None:
    validator = _load_script("validate_deployment_env")
    assert (
        validator.validate(
            {
                "POSTGRES_PASSWORD": "databasepassword123456789",
                "RENZAI_DATABASE_URL": (
                    "postgresql+asyncpg://renzai:databasepassword123456789@postgres:5432/renzai"
                ),
                "RENZAI_APP_PUBLIC_BASE_URL": "https://renzai.example",
                "RENZAI_SESSION_SECURE_COOKIE": "true",
                "RENZAI_LOGGING_JSON": "true",
                "RENZAI_SESSION_VERIFIER_KEY": "session-root-purpose-separated-123456789",
                "RENZAI_APPLICATION_KEY_VERIFIER_KEY": "app-root-purpose-separated-123456789012",
                "RENZAI_PROVIDER_CREDENTIAL_KEYS": (
                    '{"v1":"provider-root-purpose-separated-123456789"}'
                ),
                "GF_SECURITY_ADMIN_PASSWORD": "grafana-password-123456789",
            }
        )
        == []
    )


def test_phase15b_assets_preserve_network_and_cardinality_boundaries() -> None:
    verifier = _load_script("verify_phase15b_assets")
    assert verifier.verify() == []


def test_exported_spans_drop_url_query_statement_and_status_secrets() -> None:
    delegate = InMemorySpanExporter()
    exporter = SafeSpanExporter(delegate, routes=frozenset({"/api/v1/invitations/{token}/accept"}))
    span = ReadableSpan(
        name="POST /api/v1/invitations/secret-token/accept",
        attributes={
            "http.method": "POST",
            "http.route": "/api/v1/invitations/{token}/accept",
            "http.url": "https://renzai.test/api/v1/invitations/secret-token/accept?search=private",
            "db.statement": "SELECT * FROM secrets WHERE value = 'private'",
            "db.operation": "SELECT",
            "redis.key": "secret-token",
        },
        status=Status(StatusCode.ERROR, "secret-token"),
    )
    exporter.export([span])
    exported = delegate.get_finished_spans()[0]
    assert exported.name == "operation"
    assert exported.attributes == {
        "http.request.method": "POST",
        "http.route": "/api/v1/invitations/{token}/accept",
        "db.operation.name": "SELECT",
    }
    assert exported.status.description is None
    assert "secret-token" not in exported.to_json()
    assert "private" not in exported.to_json()


def test_smoke_get_returns_expected_unauthorized_status_without_retry(monkeypatch) -> None:
    smoke = _load_script("smoke_compose")

    def unauthorized(*_args: object, **_kwargs: object) -> None:
        raise HTTPError(
            "http://127.0.0.1/api/v1/auth/session", 401, "Unauthorized", {}, io.BytesIO(b"")
        )

    monkeypatch.setattr(smoke.urllib.request, "urlopen", unauthorized)
    assert smoke._get("http://127.0.0.1/api/v1/auth/session", attempts=1) == (401, b"")
