"""Synchronous and asynchronous Renzai API v1 clients."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any, Literal
from urllib.parse import quote

import httpx

from renzai_sdk._protocol import (
    as_object,
    parse_ai,
    parse_analytics,
    parse_analyze,
    parse_chat,
    parse_incident,
    parse_incident_page,
    request_id_from_headers,
)
from renzai_sdk._transport import AsyncTransport, SyncTransport
from renzai_sdk.errors import RenzaiProtocolError
from renzai_sdk.models import (
    AIIntelligenceResult,
    AITaskType,
    AnalyticsDashboard,
    AnalyzeResult,
    ChatCompletion,
    ChatMessage,
    Direction,
    DisclosureMode,
    Incident,
    IncidentFilters,
    IncidentPage,
    IncidentStatus,
    JsonObject,
    RetryPolicy,
)

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DEFAULT_RETRY_POLICY = RetryPolicy()


def _segment(value: str) -> str:
    return quote(value, safe="")


def _app_headers(api_key: str) -> dict[str, str]:
    if not api_key or any(char in api_key for char in "\r\n"):
        raise ValueError("api_key must be a non-empty header-safe value")
    return {"Authorization": f"Bearer {api_key}"}


def _session_headers(session_token: str, cookie_name: str) -> dict[str, str]:
    if not session_token or any(char in session_token for char in "\r\n;"):
        raise ValueError("session_token must be a non-empty cookie-safe value")
    if cookie_name not in {"__Host-renzai_session", "renzai_session"}:
        raise ValueError("cookie_name must be a supported Renzai session cookie name")
    return {"Cookie": f"{cookie_name}={session_token}"}


def _message_payload(messages: Sequence[ChatMessage]) -> list[JsonObject]:
    if not 1 <= len(messages) <= 32:
        raise ValueError("messages must contain between 1 and 32 items")
    payload: list[JsonObject] = []
    for message in messages:
        if message.role not in {"system", "user", "assistant"}:
            raise ValueError("message role is unsupported")
        if not message.content.strip():
            raise ValueError("message content cannot be blank")
        payload.append({"role": message.role, "content": message.content})
    return payload


def _chat_body(
    *,
    model: str,
    messages: Sequence[ChatMessage],
    temperature: float | None,
    top_p: float | None,
    max_tokens: int | None,
    stop: str | Sequence[str] | None,
    presence_penalty: float | None,
    frequency_penalty: float | None,
    seed: int | None,
) -> JsonObject:
    if not model.strip():
        raise ValueError("model cannot be blank")
    if temperature is not None and not 0 <= temperature <= 2:
        raise ValueError("temperature must be between 0 and 2")
    if top_p is not None and not 0 < top_p <= 1:
        raise ValueError("top_p must be greater than 0 and at most 1")
    if max_tokens is not None and not 1 <= max_tokens <= 4096:
        raise ValueError("max_tokens must be between 1 and 4096")
    if presence_penalty is not None and not -2 <= presence_penalty <= 2:
        raise ValueError("presence_penalty must be between -2 and 2")
    if frequency_penalty is not None and not -2 <= frequency_penalty <= 2:
        raise ValueError("frequency_penalty must be between -2 and 2")
    if seed is not None and not -(2**31) <= seed <= 2**31 - 1:
        raise ValueError("seed must be a signed 32-bit integer")
    normalized_stop: str | list[str] | None = None
    if stop is not None:
        normalized_stop = stop if isinstance(stop, str) else list(stop)
        values = [normalized_stop] if isinstance(normalized_stop, str) else normalized_stop
        if not 1 <= len(values) <= 4 or any(not value or len(value) > 1024 for value in values):
            raise ValueError("stop must contain one to four bounded strings")
    body: JsonObject = {"model": model, "messages": _message_payload(messages), "stream": False}
    optional: dict[str, object | None] = {
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stop": normalized_stop,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "seed": seed,
    }
    body.update({key: value for key, value in optional.items() if value is not None})
    return body


def _incident_params(
    filters: IncidentFilters | None, cursor: str | None, limit: int
) -> list[tuple[str, str]]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    params: list[tuple[str, str]] = [("limit", str(limit))]
    if cursor is not None:
        params.append(("cursor", cursor))
    if filters is None:
        return params
    params.extend(("status", item.value) for item in filters.statuses)
    params.extend(("severity", item.value) for item in filters.severities)
    scalar = {
        "application_id": filters.application_id,
        "environment_id": filters.environment_id,
        "assignee_user_id": filters.assignee_user_id,
        "source": filters.source,
        "action": filters.action.value if filters.action else None,
        "category": filters.category,
        "from": filters.created_from,
        "to": filters.created_to,
        "search": filters.search,
    }
    params.extend((key, str(value)) for key, value in scalar.items() if value is not None)
    if filters.unassigned:
        params.append(("unassigned", "true"))
    return params


class _SyncGateway:
    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create(
        self,
        *,
        model: str,
        messages: Sequence[ChatMessage],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stop: str | Sequence[str] | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        seed: int | None = None,
    ) -> ChatCompletion:
        body = _chat_body(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            seed=seed,
        )
        response = self._transport.request(
            "POST", "/v1/chat/completions", json_body=body, route_template="/v1/chat/completions"
        )
        return parse_chat(response.data, response.headers)


class _AsyncGateway:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create(
        self,
        *,
        model: str,
        messages: Sequence[ChatMessage],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stop: str | Sequence[str] | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
        seed: int | None = None,
    ) -> ChatCompletion:
        body = _chat_body(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            seed=seed,
        )
        response = await self._transport.request(
            "POST", "/v1/chat/completions", json_body=body, route_template="/v1/chat/completions"
        )
        return parse_chat(response.data, response.headers)


class Renzai:
    """Synchronous application-key client for Analyze and limited Gateway traffic."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT_SECONDS,
        retry: RetryPolicy = DEFAULT_RETRY_POLICY,
        transport: httpx.BaseTransport | None = None,
        logger: logging.Logger | None = None,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self._transport = SyncTransport(
            base_url=base_url,
            headers=_app_headers(api_key),
            timeout=timeout,
            retry=retry,
            transport=transport,
            logger=logger,
            max_response_bytes=max_response_bytes,
        )
        self.gateway = _SyncGateway(self._transport)

    def __repr__(self) -> str:
        return f"Renzai(base_url={self._transport.base_url!r})"

    def __enter__(self) -> Renzai:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._transport.close()

    def analyze(
        self,
        *,
        content: str,
        direction: Direction | Literal["input", "output"],
        correlation_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AnalyzeResult:
        body: JsonObject = {"content": content, "direction": Direction(direction).value}
        if correlation_id is not None:
            body["correlation_id"] = correlation_id
        if metadata is not None:
            body["metadata"] = metadata
        response = self._transport.request(
            "POST", "/api/v1/analyze", json_body=body, route_template="/api/v1/analyze"
        )
        return parse_analyze(response.data, request_id_from_headers(response.headers))


class AsyncRenzai:
    """Asynchronous application-key client for Analyze and limited Gateway traffic."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT_SECONDS,
        retry: RetryPolicy = DEFAULT_RETRY_POLICY,
        transport: httpx.AsyncBaseTransport | None = None,
        logger: logging.Logger | None = None,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self._transport = AsyncTransport(
            base_url=base_url,
            headers=_app_headers(api_key),
            timeout=timeout,
            retry=retry,
            transport=transport,
            logger=logger,
            max_response_bytes=max_response_bytes,
        )
        self.gateway = _AsyncGateway(self._transport)

    def __repr__(self) -> str:
        return f"AsyncRenzai(base_url={self._transport.base_url!r})"

    async def __aenter__(self) -> AsyncRenzai:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._transport.close()

    async def analyze(
        self,
        *,
        content: str,
        direction: Direction | Literal["input", "output"],
        correlation_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AnalyzeResult:
        body: JsonObject = {"content": content, "direction": Direction(direction).value}
        if correlation_id is not None:
            body["correlation_id"] = correlation_id
        if metadata is not None:
            body["metadata"] = metadata
        response = await self._transport.request(
            "POST", "/api/v1/analyze", json_body=body, route_template="/api/v1/analyze"
        )
        return parse_analyze(response.data, request_id_from_headers(response.headers))


class RenzaiSession:
    """Explicit server-side session client for implemented organization read/write APIs."""

    def __init__(
        self,
        *,
        session_token: str,
        csrf_token: str,
        base_url: str,
        cookie_name: str = "__Host-renzai_session",
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT_SECONDS,
        retry: RetryPolicy = DEFAULT_RETRY_POLICY,
        transport: httpx.BaseTransport | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if not csrf_token or any(char in csrf_token for char in "\r\n"):
            raise ValueError("csrf_token must be a non-empty header-safe value")
        self._csrf_token = csrf_token
        self._transport = SyncTransport(
            base_url=base_url,
            headers=_session_headers(session_token, cookie_name),
            timeout=timeout,
            retry=retry,
            transport=transport,
            logger=logger,
            max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
        )

    def __repr__(self) -> str:
        return f"RenzaiSession(base_url={self._transport.base_url!r})"

    def __enter__(self) -> RenzaiSession:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._transport.close()

    def list_incidents(
        self,
        organization_id: str,
        *,
        filters: IncidentFilters | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> IncidentPage:
        response = self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents",
            params=_incident_params(filters, cursor, limit),
            route_template="/api/v1/organizations/{organization_id}/incidents",
        )
        return parse_incident_page(response.data, request_id_from_headers(response.headers))

    def iter_incidents(
        self,
        organization_id: str,
        *,
        filters: IncidentFilters | None = None,
        page_size: int = 50,
        max_pages: int = 100,
    ) -> Iterator[Incident]:
        if not 1 <= max_pages <= 1000:
            raise ValueError("max_pages must be between 1 and 1000")
        cursor: str | None = None
        seen: set[str] = set()
        for _ in range(max_pages):
            page = self.list_incidents(
                organization_id, filters=filters, cursor=cursor, limit=page_size
            )
            yield from page.items
            if page.next_cursor is None:
                return
            if page.next_cursor in seen:
                raise RenzaiProtocolError(
                    "Renzai repeated a pagination cursor.", code="protocol_error"
                )
            seen.add(page.next_cursor)
            cursor = page.next_cursor
        raise RenzaiProtocolError("Incident pagination exceeded max_pages.", code="protocol_error")

    def get_incident(self, organization_id: str, incident_id: str) -> Incident:
        response = self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/{_segment(incident_id)}",
            route_template="/api/v1/organizations/{organization_id}/incidents/{incident_id}",
        )
        return parse_incident(response.data)

    def update_incident_status(
        self,
        organization_id: str,
        incident_id: str,
        *,
        status: IncidentStatus,
        version: int,
        reason: str | None = None,
    ) -> Incident:
        body: JsonObject = {"status": status.value, "version": version}
        if reason is not None:
            body["reason"] = reason
        response = self._write(
            "PATCH",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/status",
            body,
            "/api/v1/organizations/{organization_id}/incidents/{incident_id}/status",
        )
        return parse_incident(response.data)

    def assign_incident(
        self,
        organization_id: str,
        incident_id: str,
        *,
        assignee_user_id: str | None,
        version: int,
    ) -> Incident:
        response = self._write(
            "PATCH",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/assignment",
            {"assignee_user_id": assignee_user_id, "version": version},
            "/api/v1/organizations/{organization_id}/incidents/{incident_id}/assignment",
        )
        return parse_incident(response.data)

    def add_incident_comment(
        self, organization_id: str, incident_id: str, *, body: str
    ) -> JsonObject:
        response = self._write(
            "POST",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/comments",
            {"body": body},
            "/api/v1/organizations/{organization_id}/incidents/{incident_id}/comments",
        )
        return as_object(response.data, "incident comment")

    def analytics(
        self,
        organization_id: str,
        *,
        window: Literal["24h", "7d", "30d", "90d"] = "24h",
        application_id: str | None = None,
        environment_id: str | None = None,
        source: Literal["analyze", "playground", "gateway"] | None = None,
    ) -> AnalyticsDashboard:
        params: dict[str, str] = {"window": window}
        params.update(
            {
                key: value
                for key, value in {
                    "application_id": application_id,
                    "environment_id": environment_id,
                    "source": source,
                }.items()
                if value is not None
            }
        )
        response = self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/analytics/dashboard",
            params=params,
            route_template="/api/v1/organizations/{organization_id}/analytics/dashboard",
        )
        return parse_analytics(response.data, request_id_from_headers(response.headers))

    def request_ai(
        self,
        organization_id: str,
        incident_id: str,
        *,
        task_type: AITaskType,
        disclosure_mode: DisclosureMode = DisclosureMode.REDACTED,
        idempotency_key: str | None = None,
    ) -> AIIntelligenceResult:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key is not None else None
        response = self._write(
            "POST",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/ai-analysis",
            {"task_type": task_type.value, "disclosure_mode": disclosure_mode.value},
            "/api/v1/organizations/{organization_id}/incidents/{incident_id}/ai-analysis",
            extra_headers=headers,
        )
        return parse_ai(response.data, request_id_from_headers(response.headers))

    def list_ai(self, organization_id: str, incident_id: str) -> tuple[AIIntelligenceResult, ...]:
        response = self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/ai-analysis",
            route_template="/api/v1/organizations/{organization_id}/incidents/{incident_id}/ai-analysis",
        )
        data = as_object(response.data, "AI intelligence list")
        items = data.get("items")
        if not isinstance(items, list):
            raise RenzaiProtocolError("Renzai returned a malformed AI list.", code="protocol_error")
        request_id = request_id_from_headers(response.headers)
        return tuple(parse_ai(item, request_id) for item in items)

    def get_ai(self, organization_id: str, request_id: str) -> AIIntelligenceResult:
        response = self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/ai-analysis/{_segment(request_id)}",
            route_template="/api/v1/organizations/{organization_id}/ai-analysis/{request_id}",
        )
        return parse_ai(response.data, request_id_from_headers(response.headers))

    def _write(
        self,
        method: str,
        path: str,
        body: JsonObject,
        route: str,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        headers = {"X-Renzai-CSRF": self._csrf_token, **(extra_headers or {})}
        return self._transport.request(
            method, path, json_body=body, headers=headers, route_template=route
        )


class AsyncRenzaiSession:
    """Asynchronous counterpart to :class:`RenzaiSession`."""

    def __init__(
        self,
        *,
        session_token: str,
        csrf_token: str,
        base_url: str,
        cookie_name: str = "__Host-renzai_session",
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT_SECONDS,
        retry: RetryPolicy = DEFAULT_RETRY_POLICY,
        transport: httpx.AsyncBaseTransport | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if not csrf_token or any(char in csrf_token for char in "\r\n"):
            raise ValueError("csrf_token must be a non-empty header-safe value")
        self._csrf_token = csrf_token
        self._transport = AsyncTransport(
            base_url=base_url,
            headers=_session_headers(session_token, cookie_name),
            timeout=timeout,
            retry=retry,
            transport=transport,
            logger=logger,
            max_response_bytes=DEFAULT_MAX_RESPONSE_BYTES,
        )

    def __repr__(self) -> str:
        return f"AsyncRenzaiSession(base_url={self._transport.base_url!r})"

    async def __aenter__(self) -> AsyncRenzaiSession:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._transport.close()

    async def list_incidents(
        self,
        organization_id: str,
        *,
        filters: IncidentFilters | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> IncidentPage:
        response = await self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents",
            params=_incident_params(filters, cursor, limit),
            route_template="/api/v1/organizations/{organization_id}/incidents",
        )
        return parse_incident_page(response.data, request_id_from_headers(response.headers))

    async def iter_incidents(
        self,
        organization_id: str,
        *,
        filters: IncidentFilters | None = None,
        page_size: int = 50,
        max_pages: int = 100,
    ) -> AsyncIterator[Incident]:
        if not 1 <= max_pages <= 1000:
            raise ValueError("max_pages must be between 1 and 1000")
        cursor: str | None = None
        seen: set[str] = set()
        for _ in range(max_pages):
            page = await self.list_incidents(
                organization_id, filters=filters, cursor=cursor, limit=page_size
            )
            for item in page.items:
                yield item
            if page.next_cursor is None:
                return
            if page.next_cursor in seen:
                raise RenzaiProtocolError(
                    "Renzai repeated a pagination cursor.", code="protocol_error"
                )
            seen.add(page.next_cursor)
            cursor = page.next_cursor
        raise RenzaiProtocolError("Incident pagination exceeded max_pages.", code="protocol_error")

    async def get_incident(self, organization_id: str, incident_id: str) -> Incident:
        response = await self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/{_segment(incident_id)}",
            route_template="/api/v1/organizations/{organization_id}/incidents/{incident_id}",
        )
        return parse_incident(response.data)

    async def update_incident_status(
        self,
        organization_id: str,
        incident_id: str,
        *,
        status: IncidentStatus,
        version: int,
        reason: str | None = None,
    ) -> Incident:
        body: JsonObject = {"status": status.value, "version": version}
        if reason is not None:
            body["reason"] = reason
        response = await self._write(
            "PATCH",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/status",
            body,
            "/api/v1/organizations/{organization_id}/incidents/{incident_id}/status",
        )
        return parse_incident(response.data)

    async def assign_incident(
        self,
        organization_id: str,
        incident_id: str,
        *,
        assignee_user_id: str | None,
        version: int,
    ) -> Incident:
        response = await self._write(
            "PATCH",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/assignment",
            {"assignee_user_id": assignee_user_id, "version": version},
            "/api/v1/organizations/{organization_id}/incidents/{incident_id}/assignment",
        )
        return parse_incident(response.data)

    async def add_incident_comment(
        self, organization_id: str, incident_id: str, *, body: str
    ) -> JsonObject:
        response = await self._write(
            "POST",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/comments",
            {"body": body},
            "/api/v1/organizations/{organization_id}/incidents/{incident_id}/comments",
        )
        return as_object(response.data, "incident comment")

    async def analytics(
        self,
        organization_id: str,
        *,
        window: Literal["24h", "7d", "30d", "90d"] = "24h",
        application_id: str | None = None,
        environment_id: str | None = None,
        source: Literal["analyze", "playground", "gateway"] | None = None,
    ) -> AnalyticsDashboard:
        params: dict[str, str] = {"window": window}
        params.update(
            {
                key: value
                for key, value in {
                    "application_id": application_id,
                    "environment_id": environment_id,
                    "source": source,
                }.items()
                if value is not None
            }
        )
        response = await self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/analytics/dashboard",
            params=params,
            route_template="/api/v1/organizations/{organization_id}/analytics/dashboard",
        )
        return parse_analytics(response.data, request_id_from_headers(response.headers))

    async def request_ai(
        self,
        organization_id: str,
        incident_id: str,
        *,
        task_type: AITaskType,
        disclosure_mode: DisclosureMode = DisclosureMode.REDACTED,
        idempotency_key: str | None = None,
    ) -> AIIntelligenceResult:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key is not None else None
        response = await self._write(
            "POST",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/ai-analysis",
            {"task_type": task_type.value, "disclosure_mode": disclosure_mode.value},
            "/api/v1/organizations/{organization_id}/incidents/{incident_id}/ai-analysis",
            extra_headers=headers,
        )
        return parse_ai(response.data, request_id_from_headers(response.headers))

    async def list_ai(
        self, organization_id: str, incident_id: str
    ) -> tuple[AIIntelligenceResult, ...]:
        response = await self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/incidents/"
            f"{_segment(incident_id)}/ai-analysis",
            route_template="/api/v1/organizations/{organization_id}/incidents/{incident_id}/ai-analysis",
        )
        data = as_object(response.data, "AI intelligence list")
        items = data.get("items")
        if not isinstance(items, list):
            raise RenzaiProtocolError("Renzai returned a malformed AI list.", code="protocol_error")
        request_id = request_id_from_headers(response.headers)
        return tuple(parse_ai(item, request_id) for item in items)

    async def get_ai(self, organization_id: str, request_id: str) -> AIIntelligenceResult:
        response = await self._transport.request(
            "GET",
            f"/api/v1/organizations/{_segment(organization_id)}/ai-analysis/{_segment(request_id)}",
            route_template="/api/v1/organizations/{organization_id}/ai-analysis/{request_id}",
        )
        return parse_ai(response.data, request_id_from_headers(response.headers))

    async def _write(
        self,
        method: str,
        path: str,
        body: JsonObject,
        route: str,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        headers = {"X-Renzai-CSRF": self._csrf_token, **(extra_headers or {})}
        return await self._transport.request(
            method, path, json_body=body, headers=headers, route_template=route
        )
