"""OpenAI-compatible non-streaming provider adapter."""

from __future__ import annotations

import json
from urllib.parse import urlsplit, urlunsplit

from renzai.infrastructure.crypto.provider_credentials import (
    CredentialDecryptionError,
    ProviderCredentialKeyRing,
    provider_credential_context,
)
from renzai.infrastructure.http.outbound import PinnedHttpClient
from renzai.modules.providers.domain import (
    ProviderChatRequest,
    ProviderCompletion,
    ProviderConfigurationFailure,
    ProviderFailure,
    ProviderRuntimeConfig,
    normalize_completion,
)


class OpenAICompatibleProvider:
    def __init__(self, client: PinnedHttpClient, key_ring: ProviderCredentialKeyRing) -> None:
        self.client = client
        self.key_ring = key_ring

    async def complete(
        self, request: ProviderChatRequest, config: ProviderRuntimeConfig
    ) -> ProviderCompletion:
        headers = {"Content-Type": "application/json"}
        credential = self._credential(config)
        if credential is not None:
            headers["Authorization"] = f"Bearer {credential}"
        payload = json.dumps(request.as_payload(), separators=(",", ":")).encode("utf-8")
        _, body = await self.client.request(
            method="POST",
            url=self._endpoint(config.base_url, "chat/completions"),
            kind=config.kind,
            headers=headers,
            body=payload,
            connect_timeout=config.connect_timeout_seconds,
            total_timeout=config.chat_timeout_seconds,
            max_response_bytes=config.response_max_bytes,
        )
        try:
            decoded = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError) as error:
            raise ProviderFailure("provider response is not valid JSON") from error
        return normalize_completion(decoded, config.model)

    async def check_health(self, config: ProviderRuntimeConfig) -> None:
        headers: dict[str, str] = {}
        credential = self._credential(config)
        if credential is not None:
            headers["Authorization"] = f"Bearer {credential}"
        await self.client.request(
            method="GET",
            url=self._endpoint(config.base_url, "models"),
            kind=config.kind,
            headers=headers,
            body=b"",
            connect_timeout=config.connect_timeout_seconds,
            total_timeout=config.health_timeout_seconds,
            max_response_bytes=min(config.response_max_bytes, 32 * 1024),
        )

    def _credential(self, config: ProviderRuntimeConfig) -> str | None:
        if config.credential_ciphertext is None or config.credential_key_id is None:
            if config.kind == "openai_compatible_remote":
                raise ProviderConfigurationFailure("remote provider credential is missing")
            return None
        try:
            credential = self.key_ring.decrypt(
                config.credential_ciphertext,
                config.credential_key_id,
                provider_credential_context(
                    config.provider_id,
                    config.organization_id,
                    config.application_id,
                    config.environment_id,
                ),
            )
            if any(ord(character) < 32 or ord(character) == 127 for character in credential):
                raise ProviderConfigurationFailure("provider credential is invalid")
            return credential
        except CredentialDecryptionError as error:
            raise ProviderConfigurationFailure("provider credential is unavailable") from error

    @staticmethod
    def _endpoint(base_url: str, suffix: str) -> str:
        parsed = urlsplit(base_url)
        path = parsed.path.rstrip("/")
        if path.endswith("/v1"):
            path = f"{path}/{suffix}"
        elif path.endswith(f"/v1/{suffix}"):
            pass
        else:
            path = f"{path}/v1/{suffix}"
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
