"""Worker logs, low-cardinality metrics, and optional traces."""
# mypy: disable-error-code=untyped-decorator

from __future__ import annotations

from contextvars import Token
from threading import Lock
from time import perf_counter
from typing import Any

import structlog
from celery import Celery, signals
from prometheus_client import start_http_server

from renzai.core.config import Settings
from renzai.core.request_context import bind_request_id, create_request_id, reset_request_id
from renzai.infrastructure.observability.metrics import record_worker_task
from renzai.infrastructure.observability.telemetry import (
    TelemetryRuntime,
    configure_worker_telemetry,
)

_started: dict[str, float] = {}
_tokens: dict[str, Token[str | None]] = {}
_lock = Lock()
_metrics_started = False
_telemetry = TelemetryRuntime()


def configure_worker_observability(app: Celery, settings: Settings) -> None:
    """Register worker hooks without changing task arguments or delivery semantics."""
    global _telemetry
    _telemetry = configure_worker_telemetry(settings.observability, settings.app.environment)

    @signals.worker_ready.connect(weak=False)
    def worker_ready(**_: Any) -> None:
        global _metrics_started
        if settings.observability.metrics_enabled and not _metrics_started:
            try:
                # The port is reachable only on the internal observability network in Compose.
                start_http_server(
                    settings.observability.worker_metrics_port,
                    addr="0.0.0.0",  # noqa: S104
                )
                _metrics_started = True
            except OSError:
                structlog.get_logger("worker").warning("worker_metrics_unavailable")
        structlog.get_logger("worker").info("worker_ready", broker="redis")

    @signals.task_prerun.connect(weak=False)
    def task_prerun(task_id: str, task: Any, **_: Any) -> None:
        headers = getattr(getattr(task, "request", None), "headers", None) or {}
        inbound = headers.get("x-renzai-request-id") if isinstance(headers, dict) else None
        correlation_id = create_request_id(inbound if isinstance(inbound, str) else task_id)
        with _lock:
            _started[task_id] = perf_counter()
            _tokens[task_id] = bind_request_id(correlation_id)
        structlog.get_logger("worker").info(
            "task_started", task=_safe_task_name(getattr(task, "name", ""))
        )

    @signals.task_postrun.connect(weak=False)
    def task_postrun(task_id: str, task: Any, state: str, **_: Any) -> None:
        status = "succeeded" if state == "SUCCESS" else "failed"
        _finish(task_id, getattr(task, "name", ""), status)

    @signals.task_failure.connect(weak=False)
    def task_failure(task_id: str, sender: Any, **_: Any) -> None:
        _finish(task_id, getattr(sender, "name", ""), "failed")

    @signals.task_retry.connect(weak=False)
    def task_retry(request: Any, sender: Any, **_: Any) -> None:
        _finish(str(getattr(request, "id", "unknown")), getattr(sender, "name", ""), "retried")

    @signals.worker_shutdown.connect(weak=False)
    def worker_shutdown(**_: Any) -> None:
        structlog.get_logger("worker").info("worker_shutdown")
        _telemetry.shutdown()

    app.conf.update(worker_send_task_events=True, task_send_sent_event=True)


def _finish(task_id: str, task_name: str, status: str) -> None:
    with _lock:
        started = _started.pop(task_id, None)
        token = _tokens.pop(task_id, None)
    if started is None:
        return
    duration = perf_counter() - started
    record_worker_task(task_name, status, duration)
    structlog.get_logger("worker").info(
        "task_completed",
        task=_safe_task_name(task_name),
        status=status,
        duration_ms=round(duration * 1000, 3),
    )
    if token is not None:
        reset_request_id(token)


def _safe_task_name(task_name: str) -> str:
    if task_name == "renzai.ai_intelligence.process":
        return "ai_intelligence_process"
    if task_name == "renzai.diagnostics.echo_request_id":
        return "diagnostics_echo"
    return "other"
