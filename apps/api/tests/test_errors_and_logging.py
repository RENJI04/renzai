from __future__ import annotations

from renzai.app import _safe_log_path
from renzai.core.errors import ValidationError, error_response
from renzai.core.logging import redact_sensitive_fields


def test_stable_error_envelope_includes_request_id() -> None:
    response = error_response(
        ValidationError(details={"fields": ["email"]}), request_id="test-request"
    )
    assert response.status_code == 422
    assert response.body == (
        b'{"error":{"code":"validation","message":"The request is invalid.",'
        b'"request_id":"test-request","details":{"fields":["email"]}}}'
    )


def test_obvious_secret_and_body_fields_are_redacted() -> None:
    event = {
        "api_key": "rz_prd_example",
        "nested": {"prompt": "never log this"},
        "items": [{"credential": "also secret"}],
        "status": 200,
    }
    result = redact_sensitive_fields(None, "info", event)
    assert result == {
        "api_key": "[REDACTED]",
        "nested": {"prompt": "[REDACTED]"},
        "items": [{"credential": "[REDACTED]"}],
        "status": 200,
    }


def test_invitation_bearer_is_redacted_from_access_path() -> None:
    path = "/api/v1/invitations/rziv_lookup.secret/accept"
    assert _safe_log_path(path) == "/api/v1/invitations/[REDACTED]/accept"


def test_access_path_is_bounded_and_control_characters_cannot_forge_log_lines() -> None:
    result = _safe_log_path("/api/v1/items/line\r\nforged/" + "A" * 600)
    assert "\r" not in result and "\n" not in result
    assert len(result) <= 515
