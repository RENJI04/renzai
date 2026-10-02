from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "apps" / "api" / "src"))
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from renzai_worker.celery_app import celery_app
from renzai_worker.tasks import echo_request_id, process_ai_intelligence


def test_celery_uses_safe_serializers_and_diagnostic_task() -> None:
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert echo_request_id.run("worker-test") == {"status": "ok", "request_id": "worker-test"}
    assert process_ai_intelligence.name == "renzai.ai_intelligence.process"
    assert process_ai_intelligence.max_retries == 0
