"""FastAPI application factory through the Phase 11 optional intelligence boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from renzai.api.router import api_router, root_router
from renzai.core.body_limits import GatewayBodyLimitMiddleware
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


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = create_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = bind_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            safe_path = _safe_log_path(request.url.path)
            request.scope["path"] = safe_path
            request.scope["raw_path"] = safe_path.encode("utf-8")
            structlog.get_logger("http").info(
                "request_completed",
                method=request.method,
                path=safe_path,
                status=response.status_code,
            )
            return response
        finally:
            reset_request_id(token)


def _safe_log_path(path: str) -> str:
    parts = path.split("/")
    if len(parts) >= 6 and parts[3] == "invitations" and parts[-1] == "accept":
        parts[4] = "[REDACTED]"
    return "/".join(parts)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an application without network work or feature initialization at import time."""
    resolved_settings = settings or Settings()
    configure_logging(resolved_settings.logging)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.dependencies = build_runtime_dependencies(resolved_settings)
        try:
            yield
        finally:
            await app.state.dependencies.close()

    app = FastAPI(
        title="Renzai API",
        version="0.0.0-phase-11",
        description=(
            "Renzai identity, deterministic security analysis, provider management, "
            "limited non-streaming chat Gateway, incidents, analytics, and optional "
            "AI intelligence."
        ),
        docs_url="/docs" if resolved_settings.app.expose_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if resolved_settings.app.expose_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.identity_idle_delta = timedelta(minutes=resolved_settings.session.idle_minutes)
    app.add_middleware(
        GatewayBodyLimitMiddleware, max_body_bytes=resolved_settings.gateway.max_body_bytes
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
    return app
