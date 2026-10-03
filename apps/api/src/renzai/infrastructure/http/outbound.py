"""SSRF-controlled DNS validation and IP-pinned bounded HTTP/1.1 transport."""

from __future__ import annotations

import asyncio
import ipaddress
import ssl
from dataclasses import dataclass
from socket import AF_UNSPEC, SOCK_STREAM
from urllib.parse import SplitResult, urlsplit, urlunsplit

from renzai.modules.providers.domain import (
    ProviderConfigurationFailure,
    ProviderFailure,
    ProviderTimeout,
)

_REMOTE_KIND = "openai_compatible_remote"
_LOCAL_KIND = "openai_compatible_local"
_METADATA_HOSTS = {
    "metadata",
    "metadata.google.internal",
    "metadata.azure.internal",
    "instance-data",
    "instance-data.ec2.internal",
}


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    url: str
    scheme: str
    hostname: str
    port: int
    path: str
    addresses: tuple[str, ...]


class OutboundTargetGuard:
    def __init__(self, trusted_local_hosts: tuple[str, ...]) -> None:
        self._trusted_local_hosts = frozenset(
            self._normalize_host(item) for item in trusted_local_hosts
        )

    async def resolve(self, url: str, kind: str) -> ResolvedTarget:
        normalized, parsed = self.normalize(url, kind)
        assert parsed.hostname is not None
        host = self._normalize_host(parsed.hostname)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            literal = ipaddress.ip_address(host)
            addresses: tuple[str, ...] = (str(literal),)
        except ValueError:
            addresses = await self._resolve_addresses(host, port)
        if not addresses:
            raise ProviderConfigurationFailure("provider hostname did not resolve")
        if kind == _REMOTE_KIND:
            for address in addresses:
                if self._forbidden_remote_address(address):
                    raise ProviderConfigurationFailure("remote provider destination is denied")
        return ResolvedTarget(
            url=normalized,
            scheme=parsed.scheme,
            hostname=host,
            port=port,
            path=parsed.path or "/",
            addresses=addresses,
        )

    async def _resolve_addresses(self, host: str, port: int) -> tuple[str, ...]:
        try:
            rows = await asyncio.get_running_loop().getaddrinfo(
                host, port, family=AF_UNSPEC, type=SOCK_STREAM
            )
        except OSError as error:
            raise ProviderConfigurationFailure("provider hostname did not resolve") from error
        return tuple(sorted({row[4][0].split("%", 1)[0] for row in rows}))

    def normalize(self, url: str, kind: str) -> tuple[str, SplitResult]:
        if kind not in {_REMOTE_KIND, _LOCAL_KIND}:
            raise ProviderConfigurationFailure("provider kind is unsupported")
        try:
            parsed = urlsplit(url.strip())
            _ = parsed.port
        except ValueError as error:
            raise ProviderConfigurationFailure("provider URL is malformed") from error
        if any(ord(character) < 33 or ord(character) == 127 for character in url.strip()):
            raise ProviderConfigurationFailure("provider URL contains forbidden characters")
        if (
            not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or parsed.query
        ):
            raise ProviderConfigurationFailure("provider URL contains forbidden components")
        scheme = parsed.scheme.lower()
        if kind == _REMOTE_KIND and scheme != "https":
            raise ProviderConfigurationFailure("remote providers require HTTPS")
        if kind == _LOCAL_KIND and scheme not in {"http", "https"}:
            raise ProviderConfigurationFailure("local provider scheme is unsupported")
        host = self._normalize_host(parsed.hostname)
        if host in _METADATA_HOSTS:
            raise ProviderConfigurationFailure("metadata-style destinations are denied")
        if kind == _LOCAL_KIND and host not in self._trusted_local_hosts:
            raise ProviderConfigurationFailure("local provider host is not explicitly trusted")
        port = parsed.port or (443 if scheme == "https" else 80)
        if not 1 <= port <= 65535:
            raise ProviderConfigurationFailure("provider port is invalid")
        path = parsed.path.rstrip("/") or ""
        netloc_host = f"[{host}]" if ":" in host else host
        default_port = 443 if scheme == "https" else 80
        netloc = netloc_host if port == default_port else f"{netloc_host}:{port}"
        normalized = urlunsplit((scheme, netloc, path, "", ""))
        return normalized, urlsplit(normalized)

    @staticmethod
    def _normalize_host(value: str) -> str:
        clean = value.strip().rstrip(".").lower()
        try:
            return clean.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise ProviderConfigurationFailure("provider hostname is invalid") from error

    @staticmethod
    def _forbidden_remote_address(value: str) -> bool:
        try:
            address = ipaddress.ip_address(value.split("%", 1)[0])
        except ValueError:
            return True
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        return (
            not address.is_global
            or address.is_loopback
            or address.is_private
            or address.is_link_local
            or address.is_multicast
            or address.is_unspecified
            or address.is_reserved
        )


class PinnedHttpClient:
    """Minimal non-proxying transport that connects to a guard-approved address."""

    def __init__(self, guard: OutboundTargetGuard) -> None:
        self.guard = guard

    async def request(
        self,
        *,
        method: str,
        url: str,
        kind: str,
        headers: dict[str, str],
        body: bytes,
        connect_timeout: int,
        total_timeout: int,
        max_response_bytes: int,
    ) -> tuple[int, bytes]:
        target = await self.guard.resolve(url, kind)
        try:
            async with asyncio.timeout(total_timeout):
                return await self._request_resolved(
                    target,
                    method,
                    headers,
                    body,
                    connect_timeout,
                    max_response_bytes,
                )
        except TimeoutError as error:
            raise ProviderTimeout("provider request timed out") from error
        except ProviderFailure:
            raise
        except (
            OSError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
            UnicodeError,
            ValueError,
        ) as error:
            raise ProviderFailure("provider network or protocol failure") from error

    async def _request_resolved(
        self,
        target: ResolvedTarget,
        method: str,
        headers: dict[str, str],
        body: bytes,
        connect_timeout: int,
        max_response_bytes: int,
    ) -> tuple[int, bytes]:
        tls = ssl.create_default_context() if target.scheme == "https" else None
        writer: asyncio.StreamWriter | None = None
        last_error: OSError | None = None
        for address in target.addresses:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        address,
                        target.port,
                        ssl=tls,
                        server_hostname=target.hostname if tls else None,
                    ),
                    timeout=connect_timeout,
                )
                break
            except OSError as error:
                last_error = error
        else:
            raise ProviderFailure("provider connection failed") from last_error
        assert writer is not None
        try:
            host_header = f"[{target.hostname}]" if ":" in target.hostname else target.hostname
            default_port = 443 if target.scheme == "https" else 80
            if target.port != default_port:
                host_header = f"{host_header}:{target.port}"
            request_headers = {
                "Host": host_header,
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Connection": "close",
                "Content-Length": str(len(body)),
                "User-Agent": "Renzai/phase-8",
                **headers,
            }
            head = f"{method} {target.path or '/'} HTTP/1.1\r\n" + "".join(
                f"{name}: {value}\r\n" for name, value in request_headers.items()
            )
            writer.write(head.encode("ascii") + b"\r\n" + body)
            await writer.drain()
            raw_headers = await reader.readuntil(b"\r\n\r\n")
            if len(raw_headers) > 64 * 1024:
                raise ProviderFailure("provider response headers are oversized")
            status, response_headers = self._parse_headers(raw_headers)
            if 300 <= status <= 399:
                raise ProviderFailure("provider redirects are disabled")
            if not 200 <= status <= 299:
                raise ProviderFailure("provider returned an error status")
            if response_headers.get("content-encoding", "identity").lower() != "identity":
                raise ProviderFailure("compressed provider responses are unsupported")
            if response_headers.get("transfer-encoding", "").lower() == "chunked":
                response_body = await self._read_chunked(reader, max_response_bytes)
            elif "content-length" in response_headers:
                length = int(response_headers["content-length"])
                if length < 0 or length > max_response_bytes:
                    raise ProviderFailure("provider response is oversized")
                response_body = await reader.readexactly(length)
            else:
                response_body = await reader.read(max_response_bytes + 1)
                if len(response_body) > max_response_bytes:
                    raise ProviderFailure("provider response is oversized")
            return status, response_body
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    def _parse_headers(raw: bytes) -> tuple[int, dict[str, str]]:
        lines = raw.decode("iso-8859-1").split("\r\n")
        parts = lines[0].split(" ", 2)
        if len(parts) < 2 or not parts[0].startswith("HTTP/1."):
            raise ProviderFailure("provider status line is invalid")
        status = int(parts[1])
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if not line:
                continue
            if ":" not in line:
                raise ProviderFailure("provider response header is invalid")
            name, value = line.split(":", 1)
            normalized_name = name.strip().lower()
            normalized_value = value.strip()
            if (
                not normalized_name
                or any(
                    character.isspace() or ord(character) < 33 or ord(character) == 127
                    for character in normalized_name
                )
                or any(
                    ord(character) < 32 or ord(character) == 127 for character in normalized_value
                )
            ):
                raise ProviderFailure("provider response header is invalid")
            if (
                normalized_name in {"content-length", "transfer-encoding"}
                and normalized_name in headers
            ):
                raise ProviderFailure("provider response framing header is duplicated")
            headers[normalized_name] = normalized_value
        if "content-length" in headers and "transfer-encoding" in headers:
            raise ProviderFailure("provider response framing is ambiguous")
        transfer_encoding = headers.get("transfer-encoding")
        if transfer_encoding is not None and transfer_encoding.lower() != "chunked":
            raise ProviderFailure("provider response framing is unsupported")
        return status, headers

    @staticmethod
    async def _read_chunked(reader: asyncio.StreamReader, maximum: int) -> bytes:
        result = bytearray()
        while True:
            line = await reader.readline()
            if len(line) > 128 or not line.endswith(b"\r\n"):
                raise ProviderFailure("provider chunk framing is invalid")
            try:
                size = int(line.split(b";", 1)[0].strip(), 16)
            except ValueError as error:
                raise ProviderFailure("provider chunk size is invalid") from error
            if size == 0:
                while await reader.readline() not in {b"\r\n", b""}:
                    pass
                return bytes(result)
            if size > maximum - len(result):
                raise ProviderFailure("provider response is oversized")
            result.extend(await reader.readexactly(size))
            if await reader.readexactly(2) != b"\r\n":
                raise ProviderFailure("provider chunk framing is invalid")
