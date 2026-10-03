"""Structured logging with a conservative field redactor."""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

from renzai.core.config import LoggingConfig
from renzai.core.request_context import get_request_id

_SENSITIVE_FIELD_PARTS = {
    "api_key",
    "authorization",
    "content",
    "cookie",
    "credential",
    "password",
    "prompt",
    "response",
    "secret",
    "session",
    "token",
}


def redact_sensitive_fields(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Replace obvious secret/body fields without attempting to inspect their values."""
    for key, value in list(event_dict.items()):
        normalized = key.lower().replace("-", "_")
        if any(part in normalized for part in _SENSITIVE_FIELD_PARTS):
            event_dict[key] = "[REDACTED]"
        else:
            event_dict[key] = _redact_nested(_, __, value)
    return event_dict


def _redact_nested(_: Any, __: str, value: Any) -> Any:
    if isinstance(value, Mapping):
        return redact_sensitive_fields(_, __, dict(value))
    if isinstance(value, list):
        return [_redact_nested(_, __, item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_nested(_, __, item) for item in value)
    return value


def add_request_context(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    if request_id := get_request_id():
        event_dict.setdefault("request_id", request_id)
    return event_dict


def configure_logging(config: LoggingConfig) -> None:
    """Configure standard-library and structlog output once application creation begins."""
    logging.basicConfig(
        stream=sys.stdout, level=config.level.upper(), format="%(message)s", force=True
    )
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if config.json_logs else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_request_context,
            redact_sensitive_fields,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
