"""Bounded HTTP transports with conservative retry behavior."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from renzai_sdk._protocol import raise_error, request_id_from_headers
from renzai_sdk.errors import RenzaiConnectionError, RenzaiProtocolError, RenzaiTimeoutError
from renzai_sdk.models import JsonObject, RetryPolicy

SDK_USER_AGENT = "Renzai-Python/0.1.0"


@dataclass(frozen=True, slots=True)
class TransportResponse:
    data: object
    headers: dict[str, str]
    status_code: int


def normalize_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "base_url must be an absolute HTTP(S) URL without credentials, query, or fragment"
        )
    return value.rstrip("/")


def _retry_after(headers: httpx.Headers, maximum: float) -> float | None:
    value = headers.get("Retry-After")
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return min(maximum, max(0.0, seconds))


def _decode(content: bytes, status_code: int, headers: dict[str, str]) -> object:
    try:
        payload: object = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RenzaiProtocolError(
            "Renzai returned malformed JSON.",
            code="protocol_error",
            request_id=request_id_from_headers(headers),
            status_code=status_code,
        ) from error
    if not 200 <= status_code < 300:
        raise_error(payload, status_code, headers)
    return payload


def _validate_response_limit(value: int) -> int:
    if not 1 <= value <= 20 * 1024 * 1024:
        raise ValueError("max_response_bytes must be between 1 and 20971520")
    return value


def _query_params(
    value: list[tuple[str, str]] | dict[str, str] | None,
) -> httpx.QueryParams:
    result = httpx.QueryParams()
    items = value.items() if isinstance(value, dict) else value or []
    for key, item in items:
        result = result.add(key, item)
    return result


def _bounded_bytes(response: httpx.Response, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > maximum:
            raise RenzaiProtocolError(
                "Renzai response exceeded the configured size limit.",
                code="protocol_error",
                request_id=request_id_from_headers(response.headers),
                status_code=response.status_code,
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def _async_bounded_bytes(response: httpx.Response, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > maximum:
            raise RenzaiProtocolError(
                "Renzai response exceeded the configured size limit.",
                code="protocol_error",
                request_id=request_id_from_headers(response.headers),
                status_code=response.status_code,
            )
        chunks.append(chunk)
    return b"".join(chunks)


class SyncTransport:
    def __init__(
        self,
        *,
        base_url: str,
        headers: dict[str, str],
        timeout: float | httpx.Timeout,
        retry: RetryPolicy,
        transport: httpx.BaseTransport | None,
        logger: logging.Logger | None,
        max_response_bytes: int,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.retry = retry
        self.logger = logger
        self.max_response_bytes = _validate_response_limit(max_response_bytes)
        self.client = httpx.Client(
            headers={"User-Agent": SDK_USER_AGENT, "Accept": "application/json", **headers},
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    def close(self) -> None:
        self.client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: JsonObject | None = None,
        params: list[tuple[str, str]] | dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        route_template: str | None = None,
    ) -> TransportResponse:
        attempt = 0
        request_params = _query_params(params)
        while True:
            attempt += 1
            started = time.monotonic()
            try:
                with self.client.stream(
                    method,
                    f"{self.base_url}{path}",
                    json=json_body,
                    params=request_params,
                    headers=headers,
                ) as response:
                    self._log(method, route_template or path, response, started)
                    if (
                        method == "GET"
                        and response.status_code == 429
                        and attempt < self.retry.max_attempts
                    ):
                        delay = _retry_after(response.headers, self.retry.maximum_backoff_seconds)
                        if delay is not None:
                            time.sleep(delay)
                            continue
                    content = _bounded_bytes(response, self.max_response_bytes)
                    header_map = dict(response.headers)
            except httpx.TimeoutException as error:
                raise RenzaiTimeoutError("The Renzai request timed out.", code="timeout") from error
            except httpx.ConnectError as error:
                if method == "GET" and attempt < self.retry.max_attempts:
                    self._sleep(attempt)
                    continue
                raise RenzaiConnectionError(
                    "The Renzai server could not be reached.", code="connection_error"
                ) from error
            return TransportResponse(
                _decode(content, response.status_code, header_map), header_map, response.status_code
            )

    def _sleep(self, attempt: int) -> None:
        delay = min(
            self.retry.maximum_backoff_seconds,
            self.retry.initial_backoff_seconds * (2 ** (attempt - 1)),
        )
        time.sleep(delay)

    def _log(self, method: str, route: str, response: httpx.Response, started: float) -> None:
        if self.logger is not None:
            self.logger.debug(
                "Renzai request completed method=%s route=%s status=%s "
                "request_id=%s duration_ms=%s",
                method,
                route,
                response.status_code,
                request_id_from_headers(response.headers),
                round((time.monotonic() - started) * 1000),
            )


class AsyncTransport:
    def __init__(
        self,
        *,
        base_url: str,
        headers: dict[str, str],
        timeout: float | httpx.Timeout,
        retry: RetryPolicy,
        transport: httpx.AsyncBaseTransport | None,
        logger: logging.Logger | None,
        max_response_bytes: int,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.retry = retry
        self.logger = logger
        self.max_response_bytes = _validate_response_limit(max_response_bytes)
        self.client = httpx.AsyncClient(
            headers={"User-Agent": SDK_USER_AGENT, "Accept": "application/json", **headers},
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: JsonObject | None = None,
        params: list[tuple[str, str]] | dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        route_template: str | None = None,
    ) -> TransportResponse:
        import asyncio

        attempt = 0
        request_params = _query_params(params)
        while True:
            attempt += 1
            started = time.monotonic()
            try:
                async with self.client.stream(
                    method,
                    f"{self.base_url}{path}",
                    json=json_body,
                    params=request_params,
                    headers=headers,
                ) as response:
                    self._log(method, route_template or path, response, started)
                    if (
                        method == "GET"
                        and response.status_code == 429
                        and attempt < self.retry.max_attempts
                    ):
                        delay = _retry_after(response.headers, self.retry.maximum_backoff_seconds)
                        if delay is not None:
                            await asyncio.sleep(delay)
                            continue
                    content = await _async_bounded_bytes(response, self.max_response_bytes)
                    header_map = dict(response.headers)
            except httpx.TimeoutException as error:
                raise RenzaiTimeoutError("The Renzai request timed out.", code="timeout") from error
            except httpx.ConnectError as error:
                if method == "GET" and attempt < self.retry.max_attempts:
                    await self._sleep(attempt)
                    continue
                raise RenzaiConnectionError(
                    "The Renzai server could not be reached.", code="connection_error"
                ) from error
            return TransportResponse(
                _decode(content, response.status_code, header_map), header_map, response.status_code
            )

    async def _sleep(self, attempt: int) -> None:
        import asyncio

        delay = min(
            self.retry.maximum_backoff_seconds,
            self.retry.initial_backoff_seconds * (2 ** (attempt - 1)),
        )
        await asyncio.sleep(delay)

    def _log(self, method: str, route: str, response: httpx.Response, started: float) -> None:
        if self.logger is not None:
            self.logger.debug(
                "Renzai request completed method=%s route=%s status=%s "
                "request_id=%s duration_ms=%s",
                method,
                route,
                response.status_code,
                request_id_from_headers(response.headers),
                round((time.monotonic() - started) * 1000),
            )
