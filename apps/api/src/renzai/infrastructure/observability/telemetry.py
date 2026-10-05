"""Optional, content-free OpenTelemetry wiring."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import structlog
from fastapi import FastAPI
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace.status import Status
from sqlalchemy.ext.asyncio import AsyncEngine

from renzai.core.config import Environment, ObservabilityConfig

_HTTP_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
_DB_OPERATIONS = frozenset({"SELECT", "INSERT", "UPDATE", "DELETE", "BEGIN", "COMMIT", "ROLLBACK"})


class SafeSpanExporter(SpanExporter):
    """Allowlist exported span metadata, including attributes added by instrumentation."""

    def __init__(self, delegate: SpanExporter, *, routes: frozenset[str] = frozenset()) -> None:
        self._delegate = delegate
        self._routes = routes

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self._delegate.export([self._safe_span(span) for span in spans])

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._delegate.force_flush(timeout_millis)

    def _safe_span(self, span: ReadableSpan) -> ReadableSpan:
        scope = span.instrumentation_scope
        scope_name = scope.name if scope is not None else ""
        name = "operation"
        if "fastapi" in scope_name or "asgi" in scope_name:
            name = "http.server"
        elif "httpx" in scope_name:
            name = "http.client"
        elif "sqlalchemy" in scope_name:
            name = "db.operation"
        elif "redis" in scope_name:
            name = "redis.command"
        elif "celery" in scope_name:
            name = "worker.task"

        source = span.attributes or {}
        attributes: dict[str, str | int] = {}
        method = source.get("http.request.method", source.get("http.method"))
        if isinstance(method, str) and method in _HTTP_METHODS:
            attributes["http.request.method"] = method
        route = source.get("http.route")
        if isinstance(route, str) and route in self._routes:
            attributes["http.route"] = route
        status_code = source.get("http.response.status_code", source.get("http.status_code"))
        if isinstance(status_code, int) and 100 <= status_code <= 599:
            attributes["http.response.status_code"] = status_code
        operation = source.get("db.operation.name", source.get("db.operation"))
        if isinstance(operation, str):
            operation_name = cast(str, operation).upper()
            if operation_name in _DB_OPERATIONS:
                attributes["db.operation.name"] = operation_name

        return ReadableSpan(
            name=name,
            context=span.context,
            parent=span.parent,
            resource=span.resource,
            attributes=attributes,
            events=(),
            links=(),
            kind=span.kind,
            status=Status(span.status.status_code),
            start_time=span.start_time,
            end_time=span.end_time,
            instrumentation_scope=scope,
        )


@dataclass(slots=True)
class TelemetryRuntime:
    provider: TracerProvider | None = None

    def instrument_database(self, engine: AsyncEngine) -> None:
        if self.provider is None:
            return
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,
            tracer_provider=self.provider,
            enable_commenter=False,
        )

    def shutdown(self) -> None:
        if self.provider is not None:
            self.provider.shutdown()


def configure_api_telemetry(
    app: FastAPI, config: ObservabilityConfig, environment: Environment
) -> TelemetryRuntime:
    """Configure bounded traces; disabled telemetry adds no exporter or middleware."""
    if not config.tracing_enabled or not config.otlp_traces_endpoint:
        return TelemetryRuntime()

    routes = frozenset(
        path for route in app.routes if isinstance(path := getattr(route, "path", None), str)
    )
    provider = _provider(config, environment, routes=routes)
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="health,ready,metrics",
    )
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
    structlog.get_logger("observability").info("tracing_enabled", exporter="otlp_http")
    return TelemetryRuntime(provider)


def configure_worker_telemetry(
    config: ObservabilityConfig, environment: Environment
) -> TelemetryRuntime:
    if not config.tracing_enabled or not config.otlp_traces_endpoint:
        return TelemetryRuntime()
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    provider = _provider(config, environment)
    CeleryInstrumentor().instrument(tracer_provider=provider)  # type: ignore[no-untyped-call]
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
    SQLAlchemyInstrumentor().instrument(tracer_provider=provider, enable_commenter=False)
    structlog.get_logger("observability").info("worker_tracing_enabled", exporter="otlp_http")
    return TelemetryRuntime(provider)


def _provider(
    config: ObservabilityConfig,
    environment: Environment,
    *,
    routes: frozenset[str] = frozenset(),
) -> TracerProvider:
    resource = Resource(
        {
            "service.name": config.service_name,
            "deployment.environment.name": environment.value,
        }
    )
    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(config.trace_sample_ratio),
    )
    exporter = SafeSpanExporter(
        OTLPSpanExporter(endpoint=config.otlp_traces_endpoint), routes=routes
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider
