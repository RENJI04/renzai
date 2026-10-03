"""ASGI request-body bounds applied before JSON parsing."""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from renzai.core.errors import ValidationError, error_response
from renzai.core.request_context import REQUEST_ID_HEADER, create_request_id


class RequestBodyLimitMiddleware:
    """Bound mutating request bodies before framework JSON parsing or authentication work."""

    def __init__(
        self,
        app: ASGIApp,
        default_max_body_bytes: int,
        analyze_max_body_bytes: int,
        gateway_max_body_bytes: int,
    ) -> None:
        self.app = app
        self.default_max_body_bytes = default_max_body_bytes
        self.analyze_max_body_bytes = analyze_max_body_bytes
        self.gateway_max_body_bytes = gateway_max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            await self.app(scope, receive, send)
            return

        maximum = self._maximum(scope.get("path", ""))

        header_values = [
            value for name, value in scope.get("headers", []) if name.lower() == b"content-length"
        ]
        try:
            declared = int(header_values[0]) if len(header_values) == 1 else None
        except (UnicodeDecodeError, ValueError):
            declared = -1
        if len(header_values) > 1 or declared is not None and (declared < 0 or declared > maximum):
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
            if len(body) > maximum:
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

    def _maximum(self, path: str) -> int:
        maximum = self.default_max_body_bytes
        if path == "/v1/chat/completions":
            return min(maximum, self.gateway_max_body_bytes)
        if path == "/api/v1/analyze" or path.endswith("/playground/analyze"):
            return min(maximum, self.analyze_max_body_bytes)
        return maximum

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
