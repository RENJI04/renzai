"""ASGI request-body bounds applied before JSON parsing."""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from renzai.core.errors import ValidationError, error_response
from renzai.core.request_context import REQUEST_ID_HEADER, create_request_id


class GatewayBodyLimitMiddleware:
    """Buffer only the bounded Gateway body and reject oversized payloads early."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/v1/chat/completions"
        ):
            await self.app(scope, receive, send)
            return

        header_values = [
            value for name, value in scope.get("headers", []) if name.lower() == b"content-length"
        ]
        try:
            declared = int(header_values[0]) if len(header_values) == 1 else None
        except (UnicodeDecodeError, ValueError):
            declared = -1
        if (
            len(header_values) > 1
            or declared is not None
            and (declared < 0 or declared > self.max_body_bytes)
        ):
            await self._reject(scope, receive, send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if len(body) > self.max_body_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        inbound_id = next(
            (
                value.decode("ascii", errors="ignore")
                for name, value in scope.get("headers", [])
                if name.lower() == REQUEST_ID_HEADER.lower().encode("ascii")
            ),
            None,
        )
        request_id = create_request_id(inbound_id)
        response = error_response(
            ValidationError(details={"fields": ["body"]}), request_id=request_id
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        await response(scope, receive, send)
