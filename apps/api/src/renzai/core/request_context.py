"""Request-local correlation context that remains safe across async tasks."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def create_request_id(inbound_value: str | None) -> str:
    """Accept only bounded correlation IDs; otherwise create an opaque UUID."""
    if inbound_value and _REQUEST_ID_PATTERN.fullmatch(inbound_value):
        return inbound_value
    return str(uuid.uuid4())


def bind_request_id(request_id: str) -> Token[str | None]:
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def get_request_id() -> str | None:
    return _request_id.get()
