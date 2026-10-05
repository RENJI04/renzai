"""Safe Celery bootstrap: JSON-only, UTC and eager-test compatible."""

from __future__ import annotations

from celery import Celery

from renzai.core.config import Settings
from renzai.core.logging import configure_logging
from renzai_worker.observability import configure_worker_observability

settings = Settings()
configure_logging(settings.logging)
celery_app = Celery("renzai", broker=settings.redis.url, backend=settings.redis.url)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_time_limit=60,
    task_soft_time_limit=45,
    task_always_eager=settings.celery.task_always_eager,
)
celery_app.autodiscover_tasks(["renzai_worker"])
configure_worker_observability(celery_app, settings)
