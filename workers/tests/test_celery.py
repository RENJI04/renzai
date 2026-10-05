from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "apps" / "api" / "src"))
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from renzai_worker import tasks
from renzai_worker.celery_app import celery_app
from renzai_worker.tasks import echo_request_id, process_ai_intelligence


def test_celery_uses_safe_serializers_and_diagnostic_task() -> None:
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.worker_send_task_events is True
    assert celery_app.conf.task_send_sent_event is True
    assert echo_request_id.run("worker-test") == {"status": "ok", "request_id": "worker-test"}
    assert process_ai_intelligence.name == "renzai.ai_intelligence.process"
    assert process_ai_intelligence.max_retries == 0


def test_ai_worker_accepts_ids_only_and_duplicate_delivery_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization_id = UUID("71000000-0000-7000-8000-000000000141")
    request_id = UUID("71000000-0000-7000-8000-000000000142")
    deliveries: list[tuple[UUID, UUID]] = []

    async def fake_process(bound_organization_id: UUID, bound_request_id: UUID) -> dict[str, str]:
        deliveries.append((bound_organization_id, bound_request_id))
        return {"status": "completed", "request_id": str(bound_request_id)}

    monkeypatch.setattr(tasks, "_process", fake_process)
    first = process_ai_intelligence.run(str(organization_id), str(request_id))
    second = process_ai_intelligence.run(str(organization_id), str(request_id))
    assert first == second == {"status": "completed", "request_id": str(request_id)}
    assert deliveries == [(organization_id, request_id), (organization_id, request_id)]
    with pytest.raises(TypeError):
        process_ai_intelligence.run(str(organization_id), str(request_id), "incident content")


def test_ai_worker_rejects_non_uuid_arguments_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def fake_process(bound_organization_id: UUID, bound_request_id: UUID) -> dict[str, str]:
        nonlocal called
        called = True
        return {"status": "completed", "request_id": str(bound_request_id)}

    monkeypatch.setattr(tasks, "_process", fake_process)
    with pytest.raises(ValueError):
        process_ai_intelligence.run("not-an-id", "also-not-an-id")
    assert called is False
