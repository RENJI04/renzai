"""Framework-independent provider contracts and bounded response normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class ProviderFailure(RuntimeError):
    """Provider/network/protocol failure safe to normalize as provider_error."""


class ProviderTimeout(ProviderFailure):
    """Provider did not complete within the configured bound."""


class ProviderConfigurationFailure(ProviderFailure):
    """Stored provider configuration cannot be used safely."""


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ProviderChatRequest:
    model: str
    messages: tuple[ChatMessage, ...]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: str | tuple[str, ...] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    seed: int | None = None

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in self.messages
            ],
            "stream": False,
        }
        for field in (
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "presence_penalty",
            "frequency_penalty",
            "seed",
        ):
            value = getattr(self, field)
            if value is not None:
                payload[field] = list(value) if isinstance(value, tuple) else value
        return payload


@dataclass(frozen=True, slots=True)
class ProviderRuntimeConfig:
    provider_id: UUID
    organization_id: UUID
    application_id: UUID
    environment_id: UUID
    kind: str
    base_url: str
    model: str
    credential_ciphertext: bytes | None
    credential_key_id: str | None
    connect_timeout_seconds: int
    chat_timeout_seconds: int
    health_timeout_seconds: int
    response_max_bytes: int


@dataclass(frozen=True, slots=True)
class ProviderCompletion:
    completion_id: str
    created: int
    model: str
    content: str
    finish_reason: str
    usage: dict[str, int] | None

    def response(self, content: str | None = None) -> dict[str, object]:
        body: dict[str, object] = {
            "id": self.completion_id,
            "object": "chat.completion",
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self.content if content is None else content,
                    },
                    "finish_reason": self.finish_reason,
                }
            ],
        }
        if self.usage is not None:
            body["usage"] = self.usage
        return body


class ChatProvider(Protocol):
    async def complete(
        self, request: ProviderChatRequest, config: ProviderRuntimeConfig
    ) -> ProviderCompletion: ...

    async def check_health(self, config: ProviderRuntimeConfig) -> None: ...


def normalize_completion(payload: object, configured_model: str) -> ProviderCompletion:
    if not isinstance(payload, dict):
        raise ProviderFailure("provider response is not an object")
    completion_id = payload.get("id")
    created = payload.get("created")
    model = payload.get("model")
    choices = payload.get("choices")
    if (
        not isinstance(completion_id, str)
        or not completion_id
        or isinstance(created, bool)
        or not isinstance(created, int)
        or created < 0
        or model != configured_model
        or not isinstance(choices, list)
        or len(choices) != 1
    ):
        raise ProviderFailure("provider response shape is invalid")
    choice = choices[0]
    if not isinstance(choice, dict) or choice.get("index") not in {None, 0}:
        raise ProviderFailure("provider choice is invalid")
    message = choice.get("message")
    finish_reason = choice.get("finish_reason")
    if (
        not isinstance(message, dict)
        or message.get("role") != "assistant"
        or not isinstance(message.get("content"), str)
        or not message["content"]
        or finish_reason not in {"stop", "length"}
    ):
        raise ProviderFailure("provider assistant message is invalid")
    usage_value = payload.get("usage")
    usage: dict[str, int] | None = None
    if usage_value is not None:
        if not isinstance(usage_value, dict):
            raise ProviderFailure("provider usage is invalid")
        allowed_usage = {"prompt_tokens", "completion_tokens", "total_tokens"}
        if set(usage_value) - allowed_usage or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in usage_value.values()
        ):
            raise ProviderFailure("provider usage is invalid")
        usage = {key: value for key, value in usage_value.items() if key in allowed_usage}
    return ProviderCompletion(
        completion_id=completion_id,
        created=created,
        model=configured_model,
        content=message["content"],
        finish_reason=finish_reason,
        usage=usage,
    )
