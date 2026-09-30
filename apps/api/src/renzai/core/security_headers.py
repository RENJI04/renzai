"""Conservative headers that do not assume a frontend CSP deployment yet."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from renzai.core.config import Environment, Settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if self._settings.app.environment is Environment.PRODUCTION:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


def configure_security_headers(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
