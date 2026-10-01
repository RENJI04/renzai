"""Phase 3-compatible public error envelope without feature-specific behavior."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from renzai.core.request_context import get_request_id


class RenzaiError(Exception):
    code = "internal_error"
    message = "An unexpected error occurred."
    status_code = 500

    def __init__(self, *, details: Mapping[str, Any] | None = None) -> None:
        self.details = dict(details) if details else None
        super().__init__(self.message)


class ValidationError(RenzaiError):
    code, message, status_code = "validation", "The request is invalid.", 422


class AuthenticationError(RenzaiError):
    code, message, status_code = "authentication", "Authentication is required.", 401


class AuthorizationError(RenzaiError):
    code, message, status_code = "authorization", "You are not allowed to perform this action.", 403


class NotFoundOrHiddenError(RenzaiError):
    code, message, status_code = "not_found_or_hidden", "The resource was not found.", 404


class ConflictError(RenzaiError):
    code, message, status_code = "conflict", "The request conflicts with current state.", 409


class InvalidTransitionError(RenzaiError):
    code, message, status_code = (
        "invalid_transition",
        "The requested state transition is not allowed.",
        409,
    )


class RateLimitError(RenzaiError):
    code, message, status_code = "rate_limit", "The request rate is too high.", 429


class PolicyBlockError(RenzaiError):
    code, message, status_code = "policy_block", "The request was blocked by policy.", 403


class ReviewRequiredError(RenzaiError):
    code, message, status_code = "review_required", "The request requires review.", 409


class ProviderTimeoutError(RenzaiError):
    code, message, status_code = "provider_timeout", "The upstream provider timed out.", 504


class ProviderError(RenzaiError):
    code, message, status_code = "provider_error", "The upstream provider failed.", 502


class InspectionFailureError(RenzaiError):
    code, message, status_code = "inspection_failure", "Security inspection is unavailable.", 503


class ConfigurationError(RenzaiError):
    code, message, status_code = "configuration_error", "The service is not configured.", 503


class InternalError(RenzaiError):
    code, message, status_code = "internal_error", "An unexpected error occurred.", 500


def error_response(error: RenzaiError, request_id: str | None = None) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": error.code,
            "message": error.message,
            "request_id": request_id or get_request_id() or "unknown",
        }
    }
    if error.details:
        body["error"]["details"] = error.details
    return JSONResponse(status_code=error.status_code, content=body)


async def handle_renzai_error(request: Request, error: Exception) -> JSONResponse:
    response = error_response(cast("RenzaiError", error))
    if getattr(request.state, "clear_session_cookie", False):
        settings = request.app.state.settings.session
        name = "__Host-renzai_session" if settings.secure_cookie else "renzai_session"
        response.delete_cookie(
            name,
            secure=settings.secure_cookie,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response


async def handle_validation_error(_: Request, error: Exception) -> JSONResponse:
    validation_error = cast("RequestValidationError", error)
    fields = sorted(
        {
            str(item)
            for item in (
                entry["loc"][-1] for entry in validation_error.errors() if entry.get("loc")
            )
            if item not in {"body", "query", "path"}
        }
    )
    return error_response(ValidationError(details={"fields": fields}))


async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
    return error_response(InternalError())


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RenzaiError, handle_renzai_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
