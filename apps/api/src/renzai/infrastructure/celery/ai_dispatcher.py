"""ID-only Celery dispatch boundary for optional AI intelligence."""

from __future__ import annotations

from uuid import UUID

from celery import Celery

from renzai.core.request_context import get_request_id


class AITaskDispatcher:
    def __init__(self, broker_url: str, *, eager: bool) -> None:
        self._eager = eager
        self._client = Celery("renzai-api-dispatcher", broker=broker_url)
        self._client.conf.update(task_serializer="json", accept_content=["json"])

    def enqueue(self, organization_id: UUID, request_id: UUID) -> None:
        # Eager tests call the processor directly; production sends IDs only.
        if self._eager:
            return
        self._client.send_task(
            "renzai.ai_intelligence.process",
            args=[str(organization_id), str(request_id)],
            headers={"x-renzai-request-id": get_request_id() or ""},
        )
