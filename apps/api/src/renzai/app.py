"""FastAPI application factory for the Renzai platform."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from time import perf_counter

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from renzai.api.router import api_router, root_router
from renzai.core.body_limits import RequestBodyLimitMiddleware
from renzai.core.config import Settings
from renzai.core.errors import register_error_handlers
from renzai.core.lifecycle import build_runtime_dependencies
from renzai.core.logging import configure_logging
from renzai.core.request_context import (
    REQUEST_ID_HEADER,
    bind_request_id,
    create_request_id,
    reset_request_id,
)
from renzai.core.security_headers import configure_security_headers
from renzai.infrastructure.observability.metrics import record_http_request, render_metrics
from renzai.infrastructure.observability.telemetry import (
    TelemetryRuntime,
    configure_api_telemetry,
)

OPENAPI_TAGS = [
    {
        "name": "authentication",
        "description": "Opaque browser sessions, CSRF bootstrap, and account security.",
    },
    {
        "name": "organizations",
        "description": "Organization tenancy, membership, invitations, and role administration.",
    },
    {
        "name": "applications",
        "description": "Applications, environments, and one-time application-key lifecycle.",
    },
    {
        "name": "security",
        "description": "Deterministic Analyze and session-authenticated Security Playground.",
    },
    {
        "name": "gateway",
        "description": (
            "Limited non-streaming, text-only chat Gateway with input/output enforcement."
        ),
    },
    {
        "name": "policies",
        "description": "Versioned deterministic risk profiles and policy configuration.",
    },
    {
        "name": "providers",
        "description": "Tenant-scoped provider configuration with protected credentials.",
    },
    {
        "name": "incidents",
        "description": "Incident queue, evidence, optimistic lifecycle, assignment, and comments.",
    },
    {
        "name": "analytics",
        "description": "Privacy-bounded operational security and provider analytics.",
    },
    {
        "name": "ai-intelligence",
        "description": "Optional asynchronous advisory analysis; never authoritative enforcement.",
    },
    {"name": "health", "description": "Process liveness and dependency-aware readiness."},
]


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = create_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = bind_request_id(request_id)
        started = perf_counter()
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            safe_path = _safe_log_path(request.url.path)
            matched_route = request.scope.get("route")
            route = getattr(matched_route, "path", None)
            safe_route = route if isinstance(route, str) and route.startswith("/") else "unmatched"
            duration_seconds = perf_counter() - started
            request.scope["path"] = safe_path
            request.scope["raw_path"] = safe_path.encode("utf-8")
            structlog.get_logger("http").info(
                "request_completed",
                method=request.method,
                path=safe_route,
                route=safe_route,
                status=response.status_code,
                duration_ms=round(duration_seconds * 1000, 3),
            )
            observability = request.app.state.settings.observability
            if observability.metrics_enabled:
                record_http_request(
                    observability.service_name,
                    request.method,
                    safe_route,
                    response.status_code,
                    duration_seconds,
                )
            return response
        finally:
            reset_request_id(token)


def _safe_log_path(path: str) -> str:
    clean = "".join(
        character if ord(character) >= 32 and ord(character) != 127 else "?" for character in path
    )
    if len(clean) > 512:
        clean = f"{clean[:512]}..."
    parts = clean.split("/")
    if len(parts) >= 6 and parts[3] == "invitations" and parts[-1] == "accept":
        parts[4] = "[REDACTED]"
    return "/".join(parts)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an application without network work or feature initialization at import time."""
    resolved_settings = settings or Settings()
    configure_logging(resolved_settings.logging)
    telemetry = TelemetryRuntime()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.dependencies = build_runtime_dependencies(resolved_settings)
        telemetry.instrument_database(app.state.dependencies.database.engine)
        try:
            yield
        finally:
            await app.state.dependencies.close()
            telemetry.shutdown()

    app = FastAPI(
        title="Renzai API",
        version="1.0.0",
        description=(
            "Renzai's V1 API for deterministic security analysis, policy enforcement, "
            "limited non-streaming text Gateway, incidents, analytics, and optional advisory "
            "AI intelligence. Data-plane Analyze and Gateway calls use an environment-scoped "
            "application key as an HTTP Bearer credential. Control-plane calls use an opaque "
            "HttpOnly session cookie; state-changing calls also require the exact "
            "X-Renzai-CSRF value returned by GET /api/v1/auth/session. Error responses use the "
            "stable Renzai error envelope and include a request identifier."
        ),
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if resolved_settings.app.expose_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if resolved_settings.app.expose_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.identity_idle_delta = timedelta(minutes=resolved_settings.session.idle_minutes)
    app.add_middleware(
        RequestBodyLimitMiddleware,
        default_max_body_bytes=resolved_settings.app.max_json_body_bytes,
        analyze_max_body_bytes=resolved_settings.analyze.max_body_bytes,
        gateway_max_body_bytes=resolved_settings.gateway.max_body_bytes,
    )
    app.add_middleware(RequestContextMiddleware)
    configure_security_headers(app, resolved_settings)
    if resolved_settings.cors.origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.cors.origins),
            allow_credentials=resolved_settings.cors.allow_credentials,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["Content-Type", REQUEST_ID_HEADER, "X-Renzai-CSRF"],
        )
    register_error_handlers(app)
    app.include_router(root_router)
    app.include_router(api_router)
    if resolved_settings.observability.metrics_enabled:

        @app.get(resolved_settings.observability.metrics_path, include_in_schema=False)
        async def metrics() -> Response:
            content, content_type = render_metrics()
            return Response(
                content=content,
                headers={"Content-Type": content_type, "Cache-Control": "no-store"},
            )

    telemetry = configure_api_telemetry(
        app, resolved_settings.observability, resolved_settings.app.environment
    )
    _configure_openapi_auth(app)
    return app


def _configure_openapi_auth(app: FastAPI) -> None:
    """Describe existing authentication requirements without changing route behavior."""

    def custom_openapi() -> dict[str, object]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        components = schema.setdefault("components", {})
        assert isinstance(components, dict)
        security_schemes = components.setdefault("securitySchemes", {})
        assert isinstance(security_schemes, dict)
        security_schemes.update(
            {
                "ApplicationBearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Environment-scoped Renzai application API key.",
                },
                "SessionCookie": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "renzai_session",
                    "description": (
                        "Opaque HttpOnly session cookie. Production uses the __Host- prefix."
                    ),
                },
                "CsrfHeader": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Renzai-CSRF",
                    "description": "Required with the session cookie on state-changing routes.",
                },
            }
        )
        paths = schema.get("paths", {})
        assert isinstance(paths, dict)
        public_paths = {
            "/health",
            "/ready",
            "/api/v1/health",
            "/api/v1/ready",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/password/reset/request",
            "/api/v1/auth/password/reset/confirm",
            "/api/v1/auth/email/verification/confirm",
        }
        application_paths = {"/api/v1/analyze", "/v1/chat/completions"}
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete"} or not isinstance(
                    operation, dict
                ):
                    continue
                if path in application_paths:
                    operation["security"] = [{"ApplicationBearer": []}]
                elif path not in public_paths:
                    operation["security"] = (
                        [{"SessionCookie": [], "CsrfHeader": []}]
                        if method in {"post", "put", "patch", "delete"}
                        else [{"SessionCookie": []}]
                    )
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
