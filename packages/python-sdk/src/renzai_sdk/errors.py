"""Stable SDK exceptions mapped from the public Renzai error envelope."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class RenzaiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "internal_error",
        request_id: str | None = None,
        details: Mapping[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.request_id = request_id
        self.details = dict(details) if details is not None else None
        self.status_code = status_code
        super().__init__(message)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(code={self.code!r}, request_id={self.request_id!r}, "
            f"status_code={self.status_code!r})"
        )


class ValidationError(RenzaiError):
    pass


class AuthenticationError(RenzaiError):
    pass


class AuthorizationError(RenzaiError):
    pass


class NotFoundError(RenzaiError):
    pass


class ConflictError(RenzaiError):
    pass


class RateLimitError(RenzaiError):
    pass


class PolicyBlockError(RenzaiError):
    pass


class ReviewRequiredError(RenzaiError):
    pass


class ProviderError(RenzaiError):
    pass


class InspectionError(RenzaiError):
    pass


class ConfigurationError(RenzaiError):
    pass


class RenzaiTimeoutError(RenzaiError):
    pass


class RenzaiConnectionError(RenzaiError):
    pass


class RenzaiProtocolError(RenzaiError):
    pass


ERROR_TYPES: dict[str, type[RenzaiError]] = {
    "validation": ValidationError,
    "authentication": AuthenticationError,
    "authorization": AuthorizationError,
    "not_found_or_hidden": NotFoundError,
    "conflict": ConflictError,
    "invalid_transition": ConflictError,
    "rate_limit": RateLimitError,
    "policy_block": PolicyBlockError,
    "review_required": ReviewRequiredError,
    "provider_timeout": RenzaiTimeoutError,
    "provider_error": ProviderError,
    "inspection_failure": InspectionError,
    "configuration_error": ConfigurationError,
}
