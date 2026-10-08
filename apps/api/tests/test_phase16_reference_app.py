from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from fastapi.testclient import TestClient
from renzai_sdk import Action

ROOT = Path(__file__).parents[3]


class Result:
    def __init__(self, action: Action, redacted_content: str | None = None) -> None:
        self.action = action
        self.redacted_content = redacted_content
        self.request_id = "req_demo_reference"
        self.risk_score = 88 if action is Action.BLOCK else 0


class Protector:
    api_key = "synthetic-test-key"

    def __init__(self, result: Result) -> None:
        self.result = result

    def inspect(self, _content: str) -> Result:
        return self.result


def _module() -> ModuleType:
    path = ROOT / "examples" / "reference-app" / "app.py"
    spec = importlib.util.spec_from_file_location("renzai_reference_app", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reference_app_safe_flow_calls_synthetic_provider() -> None:
    module = _module()
    with TestClient(module.create_app(Protector(Result(Action.ALLOW)))) as client:
        response = client.post("/api/chat", json={"message": "Where is my synthetic order?"})
    assert response.status_code == 200
    assert response.json()["provider_called"] is True
    assert "Synthetic support response" in response.json()["response"]


def test_reference_app_blocked_flow_withholds_provider_content() -> None:
    module = _module()
    with TestClient(module.create_app(Protector(Result(Action.BLOCK)))) as client:
        response = client.post("/api/chat", json={"message": "Synthetic attack sample"})
    assert response.status_code == 200
    assert response.json() == {
        "decision": "block",
        "request_id": "req_demo_reference",
        "risk_score": 88,
        "provider_called": False,
        "response": None,
    }


def test_reference_app_invalid_redaction_fails_closed() -> None:
    module = _module()

    def forbidden_provider(_content: str) -> str:
        raise AssertionError("provider must not receive unredacted content")

    module.mock_provider = forbidden_provider
    with TestClient(module.create_app(Protector(Result(Action.REDACT)))) as client:
        response = client.post("/api/chat", json={"message": "Synthetic secret"})
    assert response.status_code == 502
    assert response.json() == {"detail": "Security inspection failed"}
