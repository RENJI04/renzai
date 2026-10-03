from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from conftest import ai_payload, analyze_payload, incident_payload
from renzai_sdk import (
    Action,
    AITaskType,
    AnalyticsDashboard,
    AuthenticationError,
    AuthorizationError,
    ChatMessage,
    ConfigurationError,
    ConflictError,
    Direction,
    InspectionError,
    NotFoundError,
    PolicyBlockError,
    ProviderError,
    RateLimitError,
    Renzai,
    RenzaiConnectionError,
    RenzaiError,
    RenzaiProtocolError,
    RenzaiSession,
    RenzaiTimeoutError,
    RetryPolicy,
    ReviewRequiredError,
    ValidationError,
)


def response(
    request: httpx.Request, status: int, payload: object, **headers: str
) -> httpx.Response:
    return httpx.Response(status, json=payload, headers=headers, request=request)


def test_analyze_auth_serialization_request_id_and_secret_repr() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return response(request, 200, analyze_payload(), **{"X-Request-ID": "req-1"})

    secret = "rz_dev_example_not_real"
    with Renzai(
        api_key=secret,
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.analyze(
            content="safe synthetic text",
            direction=Direction.INPUT,
            correlation_id="corr-safe",
            metadata={"feature": "test"},
        )
        client_repr = repr(client)

    assert result.action is Action.FLAG
    assert result.request_id == "req-1"
    assert seen[0].url == "https://renzai.example/api/v1/analyze"
    assert seen[0].headers["Authorization"] == f"Bearer {secret}"
    assert seen[0].headers["User-Agent"] == "Renzai-Python/0.1.0"
    assert json.loads(seen[0].content) == {
        "content": "safe synthetic text",
        "direction": "input",
        "correlation_id": "corr-safe",
        "metadata": {"feature": "test"},
    }
    assert secret not in client_repr


def test_gateway_is_strict_non_streaming_and_preserves_security_headers() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return response(
            request,
            200,
            {
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 1,
                "model": "safe-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Safe answer."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4},
            },
            **{
                "X-Renzai-Request-ID": "gateway-1",
                "X-Renzai-Input-Analysis-ID": "analysis-in",
                "X-Renzai-Output-Analysis-ID": "analysis-out",
                "X-Renzai-Input-Action": "allow",
                "X-Renzai-Output-Action": "redact",
            },
        )

    with Renzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.gateway.create(
            model="safe-model",
            messages=[ChatMessage(role="user", content="Synthetic prompt")],
            temperature=0.2,
            max_tokens=20,
        )
        with pytest.raises(TypeError):
            client.gateway.create(  # type: ignore[call-arg]
                model="safe-model",
                messages=[ChatMessage(role="user", content="Synthetic prompt")],
                stream=True,
            )

    assert seen[0] == {
        "model": "safe-model",
        "messages": [{"role": "user", "content": "Synthetic prompt"}],
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 20,
    }
    assert result.content == "Safe answer."
    assert result.request_id == "gateway-1"
    assert result.output_action is Action.REDACT


@pytest.mark.parametrize(
    ("code", "status", "expected"),
    [
        ("policy_block", 403, PolicyBlockError),
        ("review_required", 409, ReviewRequiredError),
        ("conflict", 409, ConflictError),
    ],
)
def test_error_mapping_preserves_safe_envelope(
    code: str, status: int, expected: type[RenzaiError]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response(
            request,
            status,
            {
                "error": {
                    "code": code,
                    "message": "Safe message.",
                    "request_id": "request-error",
                    "details": {"phase": "input"},
                }
            },
        )

    with Renzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(expected) as caught:
            client.analyze(content="synthetic", direction="input")
    error = caught.value
    assert error.code == code
    assert error.request_id == "request-error"
    assert "raw" not in repr(error)


@pytest.mark.parametrize(
    ("code", "status", "expected"),
    [
        ("validation", 422, ValidationError),
        ("authentication", 401, AuthenticationError),
        ("authorization", 403, AuthorizationError),
        ("not_found_or_hidden", 404, NotFoundError),
        ("rate_limit", 429, RateLimitError),
        ("provider_error", 502, ProviderError),
        ("inspection_failure", 503, InspectionError),
        ("configuration_error", 503, ConfigurationError),
        ("provider_timeout", 504, RenzaiTimeoutError),
    ],
)
def test_representative_error_matrix(code: str, status: int, expected: type[RenzaiError]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response(
            request,
            status,
            {"error": {"code": code, "message": "Safe message.", "request_id": "req"}},
        )

    with Renzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(expected):
            client.analyze(content="synthetic", direction="input")


def test_session_writes_csrf_and_idempotency_without_retry() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return response(request, 202, ai_payload(), **{"X-Request-ID": "req-ai"})

    with RenzaiSession(
        session_token="opaque-session",
        csrf_token="csrf-safe",
        cookie_name="renzai_session",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.request_ai(
            "org-1",
            "incident-1",
            task_type=AITaskType.INCIDENT_SUMMARY,
            idempotency_key="caller-key",
        )
        client_repr = repr(client)

    assert result.request_id == "ai-request-1"
    assert seen[0].headers["Cookie"] == "renzai_session=opaque-session"
    assert seen[0].headers["X-Renzai-CSRF"] == "csrf-safe"
    assert seen[0].headers["Idempotency-Key"] == "caller-key"
    assert "opaque-session" not in client_repr and "csrf-safe" not in client_repr


def test_pagination_detects_repeated_cursor() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response(
            request,
            200,
            {"items": [incident_payload(f"incident-{calls}")], "next_cursor": "repeat", "limit": 1},
        )

    with RenzaiSession(
        session_token="opaque-session",
        csrf_token="csrf-safe",
        cookie_name="renzai_session",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(RenzaiProtocolError, match="repeated"):
            list(client.iter_incidents("org-1", page_size=1))
    assert calls == 2


def test_malformed_success_is_protocol_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return response(request, 200, {"analysis_id": "partial"})

    with Renzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(RenzaiProtocolError):
            client.analyze(content="synthetic", direction="input")


def test_transport_bounds_timeout_connection_and_retry_semantics() -> None:
    calls = 0

    def retry_handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("synthetic connect failure", request=request)
        return response(request, 200, {"items": [], "next_cursor": None, "limit": 50})

    with RenzaiSession(
        session_token="opaque-session",
        csrf_token="csrf-safe",
        cookie_name="renzai_session",
        base_url="https://renzai.example",
        retry=RetryPolicy(max_attempts=2, initial_backoff_seconds=0),
        transport=httpx.MockTransport(retry_handler),
    ) as session_client:
        assert session_client.list_incidents("org-1").items == ()
    assert calls == 2

    post_calls = 0

    def connection_handler(request: httpx.Request) -> httpx.Response:
        nonlocal post_calls
        post_calls += 1
        raise httpx.ConnectError("synthetic connect failure", request=request)

    with Renzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        retry=RetryPolicy(max_attempts=3, initial_backoff_seconds=0),
        transport=httpx.MockTransport(connection_handler),
    ) as connection_client:
        with pytest.raises(RenzaiConnectionError):
            connection_client.analyze(content="synthetic", direction="input")
    assert post_calls == 1

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("synthetic timeout", request=request)

    with Renzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(timeout_handler),
    ) as timeout_client:
        with pytest.raises(RenzaiTimeoutError):
            timeout_client.analyze(content="synthetic", direction="input")

    def large_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{}   ", request=request)

    with Renzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        max_response_bytes=4,
        transport=httpx.MockTransport(large_handler),
    ) as bounded_client:
        with pytest.raises(RenzaiProtocolError, match="size limit"):
            bounded_client.analyze(content="synthetic", direction="input")


def test_analytics_ai_and_path_segments() -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if "/analytics/dashboard" in request.url.path:
            return response(
                request,
                200,
                {
                    "filters": {"window": "24h"},
                    "summary": {},
                    "activity": [],
                    "risk_distribution": [],
                    "threat_categories": [],
                    "top_detectors": [],
                    "policy_actions": [],
                    "applications": [],
                    "environments": [],
                    "providers": [],
                    "incidents": {},
                    "recent_incidents": [],
                    "query_duration_ms": 3,
                },
            )
        if request.url.path.endswith("/ai-analysis"):
            return response(request, 200, {"items": [ai_payload()]})
        return response(request, 200, incident_payload())

    with RenzaiSession(
        session_token="opaque-session",
        csrf_token="csrf-safe",
        cookie_name="renzai_session",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        dashboard = client.analytics("org/with/slash")
        incident = client.get_incident("org/with/slash", "incident/with/slash")
        ai_items = client.list_ai("org-1", "incident-1")

    assert isinstance(dashboard, AnalyticsDashboard)
    assert dashboard.query_duration_ms == 3
    assert incident.incident_id == "incident-1"
    assert ai_items[0].request_id == "ai-request-1"
    assert "%2F" in seen_urls[0] and "%2F" in seen_urls[1]


def test_invalid_response_enum_is_protocol_error() -> None:
    payload = analyze_payload()
    payload["action"] = "future-unsafe-value"

    def handler(request: httpx.Request) -> httpx.Response:
        return response(request, 200, payload)

    with Renzai(
        api_key="rz_dev_example_not_real",
        base_url="https://renzai.example",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(RenzaiProtocolError, match="invalid action"):
            client.analyze(content="synthetic", direction="input")


def test_base_url_rejects_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="absolute HTTP"):
        Renzai(
            api_key="rz_dev_example_not_real",
            base_url="https://username:password@renzai.example",
        )
