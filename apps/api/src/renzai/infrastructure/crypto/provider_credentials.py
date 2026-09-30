"""Purpose-separated authenticated encryption for provider credentials."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from os import urandom
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

_PURPOSE = b"renzai/provider-credential/aes-256-gcm/v1\x00"
_NONCE_BYTES = 12


class CredentialDecryptionError(RuntimeError):
    """Stored credential cannot be authenticated with the configured key ring."""


@dataclass(frozen=True, slots=True)
class EncryptedCredential:
    ciphertext: bytes
    key_id: str


def provider_credential_context(
    provider_id: UUID,
    organization_id: UUID,
    application_id: UUID,
    environment_id: UUID,
) -> bytes:
    return (
        f"provider={provider_id};organization={organization_id};"
        f"application={application_id};environment={environment_id}"
    ).encode("ascii")


class ProviderCredentialKeyRing:
    """AES-GCM key ring with an explicit active key and rotation-compatible reads."""

    def __init__(self, active_key_id: str, keys: Mapping[str, SecretStr | str]) -> None:
        if active_key_id not in keys:
            raise ValueError("active provider credential key ID is missing")
        if any(
            not key_id
            or len(key_id) > 80
            or any(ord(character) < 33 or ord(character) == 127 for character in key_id)
            for key_id in keys
        ):
            raise ValueError("provider credential key IDs must be bounded visible strings")
        raw_keys = {
            key_id: value.get_secret_value() if isinstance(value, SecretStr) else value
            for key_id, value in keys.items()
        }
        if any(len(value.encode("utf-8")) < 32 for value in raw_keys.values()):
            raise ValueError("provider credential encryption roots must be at least 32 bytes")
        self.active_key_id = active_key_id
        self._keys = {
            key_id: sha256(_PURPOSE + value.encode("utf-8")).digest()
            for key_id, value in raw_keys.items()
        }

    def encrypt(self, plaintext: str, context: bytes) -> EncryptedCredential:
        if not plaintext:
            raise ValueError("provider credential cannot be empty")
        nonce = urandom(_NONCE_BYTES)
        ciphertext = AESGCM(self._keys[self.active_key_id]).encrypt(
            nonce, plaintext.encode("utf-8"), context
        )
        return EncryptedCredential(nonce + ciphertext, self.active_key_id)

    def decrypt(self, encrypted: bytes, key_id: str, context: bytes) -> str:
        key = self._keys.get(key_id)
        if key is None or len(encrypted) <= _NONCE_BYTES:
            raise CredentialDecryptionError("provider credential key is unavailable")
        try:
            plaintext = AESGCM(key).decrypt(
                encrypted[:_NONCE_BYTES], encrypted[_NONCE_BYTES:], context
            )
            return plaintext.decode("utf-8")
        except (InvalidTag, UnicodeDecodeError) as error:
            raise CredentialDecryptionError("provider credential authentication failed") from error
