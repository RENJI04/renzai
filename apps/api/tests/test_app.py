from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from renzai.app import create_app
from renzai.core.config import Environment, Settings


@dataclass
class ReadinessStub:
    ready: bool

    async def is_ready(self) -> bool:
        return self.ready

    async def close(self) -> None:
        return None


def test_health_is_minimal_and_has_safe_headers() -> None:
    app = create_app(Settings(app_environment=Environment.TEST, database_url="sqlite+aiosqlite://"))
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_request_id_is_generated_and_a_valid_inbound_id_is_preserved() -> None:
    app = create_app(Settings(app_environment=Environment.TEST, database_url="sqlite+aiosqlite://"))
    with TestClient(app) as client:
        generated = client.get("/health")
        inbound = client.get("/health", headers={"X-Request-ID": "integration-42"})
        untrusted = client.get("/health", headers={"X-Request-ID": "not valid!"})
    assert generated.headers["X-Request-ID"]
    assert inbound.headers["X-Request-ID"] == "integration-42"
    assert untrusted.headers["X-Request-ID"] != "not valid!"


def test_readiness_is_minimal_and_dependency_safe() -> None:
    app = create_app(Settings(app_environment=Environment.TEST, database_url="sqlite+aiosqlite://"))
    with TestClient(app) as client:
        app.state.dependencies = ReadinessStub(ready=True)
        assert client.get("/ready").json() == {"status": "ready"}
        app.state.dependencies = ReadinessStub(ready=False)
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_metrics_are_opt_in_and_expose_only_bounded_operational_labels() -> None:
    disabled = create_app(
        Settings(app_environment=Environment.TEST, database_url="sqlite+aiosqlite://")
    )
    with TestClient(disabled) as client:
        assert client.get("/metrics").status_code == 404

    enabled = create_app(
        Settings(
            app_environment=Environment.TEST,
            database_url="sqlite+aiosqlite://",
            observability_metrics_enabled=True,
        )
    )
    with TestClient(enabled) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    body = response.text
    assert "renzai_http_requests_total" in body
    assert 'route="/health"' in body
    assert "request_id" not in body
    assert "organization_id" not in body
    assert "api_key" not in body


def test_unmatched_paths_and_unsupported_methods_do_not_create_metric_labels() -> None:
    app = create_app(
        Settings(
            app_environment=Environment.TEST,
            database_url="sqlite+aiosqlite://",
            observability_metrics_enabled=True,
        )
    )
    with TestClient(app) as client:
        assert client.get("/api/private-token-one").status_code == 404
        assert client.request("SP0OF", "/api/private-token-two").status_code == 404
        metrics = client.get("/metrics").text
    assert 'route="unmatched"' in metrics
    assert 'method="OTHER"' in metrics
    assert "private-token-one" not in metrics
    assert "private-token-two" not in metrics
    assert "SP0OF" not in metrics
