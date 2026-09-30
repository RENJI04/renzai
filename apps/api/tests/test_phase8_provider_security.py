from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import SecretStr

from renzai.infrastructure.crypto.provider_credentials import (
    CredentialDecryptionError,
    ProviderCredentialKeyRing,
    provider_credential_context,
)
from renzai.infrastructure.http.outbound import OutboundTargetGuard
from renzai.modules.providers.domain import ProviderConfigurationFailure, normalize_completion


def test_provider_credential_encryption_is_authenticated_unique_and_rotatable() -> None:
    context = provider_credential_context(
        UUID("71000000-0000-7000-8000-000000000010"),
        UUID("71000000-0000-7000-8000-000000000011"),
        UUID("71000000-0000-7000-8000-000000000012"),
        UUID("71000000-0000-7000-8000-000000000013"),
    )
    ring = ProviderCredentialKeyRing(
        "v2",
        {
            "v1": SecretStr("old-provider-root-material-0000000001"),
            "v2": SecretStr("active-provider-root-material-0000001"),
        },
    )
    first = ring.encrypt("provider-secret", context)
    second = ring.encrypt("provider-secret", context)
    assert first.key_id == second.key_id == "v2"
    assert first.ciphertext != second.ciphertext
    assert ring.decrypt(first.ciphertext, first.key_id, context) == "provider-secret"

    old_ring = ProviderCredentialKeyRing(
        "v1",
        {
            "v1": "old-provider-root-material-0000000001",
            "v2": "active-provider-root-material-0000001",
        },
    )
    old = old_ring.encrypt("old-provider-secret", context)
    assert ring.decrypt(old.ciphertext, old.key_id, context) == "old-provider-secret"

    tampered = first.ciphertext[:-1] + bytes([first.ciphertext[-1] ^ 1])
    with pytest.raises(CredentialDecryptionError):
        ring.decrypt(tampered, first.key_id, context)
    with pytest.raises(CredentialDecryptionError):
        ring.decrypt(first.ciphertext, "unknown", context)
    with pytest.raises(CredentialDecryptionError):
        ring.decrypt(first.ciphertext, first.key_id, context + b"-wrong")


def test_provider_credential_key_ring_rejects_weak_roots_and_invalid_key_ids() -> None:
    with pytest.raises(ValueError, match="at least 32 bytes"):
        ProviderCredentialKeyRing("v1", {"v1": "short-root"})
    with pytest.raises(ValueError, match="bounded visible"):
        ProviderCredentialKeyRing("bad key", {"bad key": "x" * 32})


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1",
        "https://[::1]",
        "https://10.0.0.1",
        "https://172.16.0.1",
        "https://192.168.1.1",
        "https://169.254.169.254",
        "https://[fe80::1]",
        "https://224.0.0.1",
        "https://0.0.0.0",
        "https://[::ffff:127.0.0.1]",
    ],
)
async def test_remote_ssrf_guard_rejects_forbidden_literal_targets(url: str) -> None:
    with pytest.raises(ProviderConfigurationFailure):
        await OutboundTargetGuard(()).resolve(url, "openai_compatible_remote")


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.com",
        "https://user:secret@api.example.com",
        "https://api.example.com/path?api_key=secret",
        "https://api.example.com/path#fragment",
        "https://metadata.google.internal",
    ],
)
async def test_remote_ssrf_guard_rejects_unsafe_url_components(url: str) -> None:
    with pytest.raises(ProviderConfigurationFailure):
        await OutboundTargetGuard(()).resolve(url, "openai_compatible_remote")


async def test_local_provider_requires_exact_opt_in() -> None:
    with pytest.raises(ProviderConfigurationFailure):
        await OutboundTargetGuard(()).resolve("http://127.0.0.1:11434", "openai_compatible_local")
    target = await OutboundTargetGuard(("127.0.0.1",)).resolve(
        "http://127.0.0.1:11434/v1/", "openai_compatible_local"
    )
    assert target.url == "http://127.0.0.1:11434/v1"
    assert target.addresses == ("127.0.0.1",)


async def test_remote_dns_answer_to_private_address_is_rejected() -> None:
    class PrivateDnsGuard(OutboundTargetGuard):
        async def _resolve_addresses(self, host: str, port: int) -> tuple[str, ...]:
            return ("93.184.216.34", "10.0.0.5")

    with pytest.raises(ProviderConfigurationFailure):
        await PrivateDnsGuard(()).resolve("https://provider.example/v1", "openai_compatible_remote")


def test_provider_response_normalization_is_strict_and_allowlisted() -> None:
    completion = normalize_completion(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": "safe-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello"},
                    "finish_reason": "stop",
                    "ignored": "not forwarded",
                }
            ],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            "provider_internal": "discarded",
        },
        "safe-model",
    )
    assert completion.response() == {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1,
        "model": "safe-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hello"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
    }
