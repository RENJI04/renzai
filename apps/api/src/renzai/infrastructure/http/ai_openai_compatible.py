"""OpenAI-compatible adapter dedicated to optional AI intelligence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from renzai.infrastructure.crypto.ai_credentials import (
    AICredentialDecryptionError,
    AICredentialKeyRing,
    ai_credential_context,
)
from renzai.infrastructure.http.outbound import PinnedHttpClient
from renzai.modules.ai_intelligence.domain import (
    SYSTEM_INSTRUCTION,
    AIProviderFailure,
    AIProviderTimeout,
    AITaskType,
)
from renzai.modules.providers.domain import ProviderFailure, ProviderTimeout, normalize_completion


@dataclass(frozen=True, slots=True)
class AIProviderRuntimeConfig:
    config_id: UUID
    organization_id: UUID
    kind: str
    base_url: str
    model: str
    credential_ciphertext: bytes | None
    credential_key_id: str | None
    connect_timeout_seconds: int
    request_timeout_seconds: int
    response_max_bytes: int


class OpenAICompatibleAIIntelligenceProvider:
    def __init__(self, client: PinnedHttpClient, key_ring: AICredentialKeyRing) -> None:
        self.client = client
        self.key_ring = key_ring

    async def generate(
        self,
        *,
        config: object,
        task_type: AITaskType,
        context: dict[str, object],
    ) -> tuple[str, dict[str, int] | None]:
        if not isinstance(config, AIProviderRuntimeConfig):
            raise AIProviderFailure("AI provider configuration is invalid")
        headers = {"Content-Type": "application/json"}
        credential = self._credential(config)
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
        user_data = json.dumps(
            {"requested_task": task_type.value, "untrusted_incident_data": context},
            separators=(",", ":"),
            sort_keys=True,
        )
        payload = json.dumps(
            {
                "model": config.model,
                "stream": False,
                "temperature": 0,
                "max_tokens": 2048,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": user_data},
                ],
            },
            separators=(",", ":"),
        ).encode()
        try:
            _, body = await self.client.request(
                method="POST",
                url=self._endpoint(config.base_url, "chat/completions"),
                kind=config.kind,
                headers=headers,
                body=payload,
                connect_timeout=config.connect_timeout_seconds,
                total_timeout=config.request_timeout_seconds,
                max_response_bytes=config.response_max_bytes,
            )
            completion = normalize_completion(json.loads(body), config.model)
            return completion.content, completion.usage
        except ProviderTimeout as error:
            raise AIProviderTimeout("AI provider timed out") from error
        except (ProviderFailure, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise AIProviderFailure("AI provider request failed") from error

    async def check_health(self, config: AIProviderRuntimeConfig) -> None:
        headers: dict[str, str] = {}
        credential = self._credential(config)
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
        try:
            await self.client.request(
                method="GET",
                url=self._endpoint(config.base_url, "models"),
                kind=config.kind,
                headers=headers,
                body=b"",
                connect_timeout=config.connect_timeout_seconds,
                total_timeout=min(config.request_timeout_seconds, 15),
                max_response_bytes=min(config.response_max_bytes, 32 * 1024),
            )
        except ProviderTimeout as error:
            raise AIProviderTimeout("AI provider timed out") from error
        except ProviderFailure as error:
            raise AIProviderFailure("AI provider request failed") from error

    def _credential(self, config: AIProviderRuntimeConfig) -> str | None:
        if config.credential_ciphertext is None or config.credential_key_id is None:
            if config.kind == "openai_compatible_remote":
                raise AIProviderFailure("AI provider credential is unavailable")
            return None
        try:
            credential = self.key_ring.decrypt(
                config.credential_ciphertext,
                config.credential_key_id,
                ai_credential_context(config.config_id, config.organization_id),
            )
            if any(ord(character) < 32 or ord(character) == 127 for character in credential):
                raise AIProviderFailure("AI provider credential is unavailable")
            return credential
        except AICredentialDecryptionError as error:
            raise AIProviderFailure("AI provider credential is unavailable") from error

    @staticmethod
    def _endpoint(base_url: str, suffix: str) -> str:
        parsed = urlsplit(base_url)
        path = parsed.path.rstrip("/")
        path = f"{path}/{suffix}" if path.endswith("/v1") else f"{path}/v1/{suffix}"
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
