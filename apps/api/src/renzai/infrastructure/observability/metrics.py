"""Low-cardinality Prometheus metrics for API and worker operations."""

from __future__ import annotations

from collections.abc import Mapping

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "renzai_http_requests_total",
    "Completed Renzai HTTP requests.",
    ("service", "method", "route", "status_class"),
)
HTTP_DURATION = Histogram(
    "renzai_http_request_duration_seconds",
    "Renzai HTTP request duration.",
    ("service", "method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
SECURITY_OPERATIONS = Counter(
    "renzai_security_operations_total",
    "Completed security operations by bounded operation and outcome.",
    ("operation", "outcome"),
)
WORKER_TASKS = Counter(
    "renzai_worker_tasks_total",
    "Completed Celery tasks by bounded task name and status.",
    ("task", "status"),
)
WORKER_TASK_DURATION = Histogram(
    "renzai_worker_task_duration_seconds",
    "Celery task duration by bounded task name.",
    ("task",),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
READINESS = Gauge(
    "renzai_readiness",
    "Last observed readiness state for the API process.",
)

_OPERATIONS: Mapping[str, frozenset[str]] = {
    "analysis": frozenset({"allow", "flag", "redact", "require_review", "block"}),
    "gateway": frozenset(
        {
            "completed",
            "provider_timeout",
            "provider_error",
            "configuration_error",
            "output_block",
            "output_review",
            "output_inspection_failure",
        }
    ),
    "incident": frozenset({"automatic_created", "automatic_deduplicated", "manual_created"}),
}
_TASKS = {
    "renzai.ai_intelligence.process": "ai_intelligence_process",
    "renzai.diagnostics.echo_request_id": "diagnostics_echo",
}
_HTTP_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})


def record_http_request(
    service: str,
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record a request without request, user, tenant, or content labels."""
    safe_route = route if route.startswith("/") and len(route) <= 160 else "unmatched"
    safe_method = method.upper() if method.upper() in _HTTP_METHODS else "OTHER"
    status_class = f"{status_code // 100}xx" if 100 <= status_code <= 599 else "unknown"
    try:
        HTTP_REQUESTS.labels(service, safe_method, safe_route, status_class).inc()
        HTTP_DURATION.labels(service, safe_method, safe_route).observe(duration_seconds)
    except Exception:
        return


def record_security_operation(operation: str, outcome: str) -> None:
    """Record only explicitly bounded operation/outcome values."""
    allowed = _OPERATIONS.get(operation)
    safe_outcome = outcome if allowed is not None and outcome in allowed else "other"
    safe_operation = operation if allowed is not None else "other"
    try:
        SECURITY_OPERATIONS.labels(safe_operation, safe_outcome).inc()
    except Exception:
        return


def record_worker_task(task_name: str, status: str, duration_seconds: float) -> None:
    safe_task = _TASKS.get(task_name, "other")
    safe_status = status if status in {"succeeded", "failed", "retried", "revoked"} else "other"
    try:
        WORKER_TASKS.labels(safe_task, safe_status).inc()
        WORKER_TASK_DURATION.labels(safe_task).observe(max(duration_seconds, 0.0))
    except Exception:
        return


def set_readiness(ready: bool) -> None:
    try:
        READINESS.set(1 if ready else 0)
    except Exception:
        return


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
