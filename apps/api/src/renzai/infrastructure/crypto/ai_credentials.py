"""Purpose-separated authenticated encryption for AI intelligence credentials."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from os import urandom
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

_PURPOSE = b"renzai/ai-intelligence-credential/aes-256-gcm/v1\x00"
_NONCE_BYTES = 12


class AICredentialDecryptionError(RuntimeError):
    """Stored AI credential cannot be authenticated with the configured key ring."""


@dataclass(frozen=True, slots=True)
class EncryptedAICredential:
    ciphertext: bytes
    key_id: str


def ai_credential_context(config_id: UUID, organization_id: UUID) -> bytes:
    return f"ai_config={config_id};organization={organization_id}".encode("ascii")


class AICredentialKeyRing:
    """AI-only AES-GCM purpose derived from the configured credential roots."""

    def __init__(self, active_key_id: str, keys: Mapping[str, SecretStr | str]) -> None:
        if active_key_id not in keys:
            raise ValueError("active AI credential key ID is missing")
        raw = {
            key_id: value.get_secret_value() if isinstance(value, SecretStr) else value
            for key_id, value in keys.items()
        }
        if any(not key_id or len(key_id) > 80 for key_id in raw):
            raise ValueError("AI credential key IDs must be bounded")
        if any(len(value.encode("utf-8")) < 32 for value in raw.values()):
            raise ValueError("AI credential encryption roots must be at least 32 bytes")
        self.active_key_id = active_key_id
        self._keys = {
            key_id: sha256(_PURPOSE + value.encode("utf-8")).digest()
            for key_id, value in raw.items()
        }

    def encrypt(self, plaintext: str, context: bytes) -> EncryptedAICredential:
        if not plaintext:
            raise ValueError("AI credential cannot be empty")
        nonce = urandom(_NONCE_BYTES)
        ciphertext = AESGCM(self._keys[self.active_key_id]).encrypt(
            nonce, plaintext.encode("utf-8"), context
        )
        return EncryptedAICredential(nonce + ciphertext, self.active_key_id)

    def decrypt(self, encrypted: bytes, key_id: str, context: bytes) -> str:
        key = self._keys.get(key_id)
        if key is None or len(encrypted) <= _NONCE_BYTES:
            raise AICredentialDecryptionError("AI credential key is unavailable")
        try:
            value = AESGCM(key).decrypt(encrypted[:_NONCE_BYTES], encrypted[_NONCE_BYTES:], context)
            return value.decode("utf-8")
        except (InvalidTag, UnicodeDecodeError) as error:
            raise AICredentialDecryptionError("AI credential authentication failed") from error
