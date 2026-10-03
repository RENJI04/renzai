"""Argon2id and purpose-separated opaque credential primitives."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass

from argon2 import Parameters, PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from argon2.low_level import Type

ARGON2_VERSION = 19
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 65_536
ARGON2_PARALLELISM = 4
ARGON2_HASH_LENGTH = 32
ARGON2_SALT_LENGTH = 16
_LOOKUP_LENGTH = 22
_SECRET_LENGTH = 43
_CREDENTIAL_PATTERN = re.compile(
    rf"\A([A-Za-z0-9_-]{{{_LOOKUP_LENGTH}}})\."
    rf"([A-Za-z0-9_-]{{{_SECRET_LENGTH}}})\Z"
)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass(frozen=True, slots=True)
class OpaqueCredential:
    public: str
    lookup: str
    verifier: bytes


class IdentityCrypto:
    def __init__(self, master_key: str, key_id: str) -> None:
        self._master_key = master_key.encode("utf-8")
        self.key_id = key_id
        # Keep the password cost profile explicit so library-default changes cannot
        # silently weaken or unexpectedly amplify authentication work.
        self._passwords = PasswordHasher.from_parameters(
            Parameters(
                type=Type.ID,
                version=ARGON2_VERSION,
                salt_len=ARGON2_SALT_LENGTH,
                hash_len=ARGON2_HASH_LENGTH,
                time_cost=ARGON2_TIME_COST,
                memory_cost=ARGON2_MEMORY_COST_KIB,
                parallelism=ARGON2_PARALLELISM,
            )
        )
        self._dummy_password_hash = self._passwords.hash("not-a-user-password-000000")

    def hash_password(self, password: str) -> str:
        return self._passwords.hash(password)

    def verify_password(self, encoded: str, password: str) -> tuple[bool, str | None]:
        try:
            valid = self._passwords.verify(encoded, password)
        except (VerifyMismatchError, InvalidHashError):
            return False, None
        replacement = (
            self._passwords.hash(password) if self._passwords.check_needs_rehash(encoded) else None
        )
        return valid, replacement

    def consume_dummy_password_check(self, password: str) -> None:
        try:
            self._passwords.verify(self._dummy_password_hash, password)
        except VerifyMismatchError:
            pass

    def create_credential(self, purpose: str, prefix: str = "") -> OpaqueCredential:
        lookup = _b64(secrets.token_bytes(16))
        secret = _b64(secrets.token_bytes(32))
        public = f"{prefix}{lookup}.{secret}"
        return OpaqueCredential(public, lookup, self.verifier(purpose, lookup, secret))

    def parse_and_verify(
        self,
        public: str,
        purpose: str,
        expected_lookup: str,
        expected_verifier: bytes,
        prefix: str = "",
    ) -> bool:
        if prefix and not public.startswith(prefix):
            return False
        value = public[len(prefix) :] if prefix else public
        parts = self._parts(value)
        if parts is None or not hmac.compare_digest(parts[0], expected_lookup):
            return False
        return hmac.compare_digest(self.verifier(purpose, parts[0], parts[1]), expected_verifier)

    def lookup(self, public: str, prefix: str = "") -> str | None:
        if prefix and not public.startswith(prefix):
            return None
        value = public[len(prefix) :] if prefix else public
        parts = self._parts(value)
        return parts[0] if parts is not None else None

    def verifier(self, purpose: str, lookup: str, secret: str) -> bytes:
        message = f"{purpose}\0{lookup}\0{secret}".encode()
        return hmac.new(self._purpose_key(purpose), message, hashlib.sha256).digest()

    def csrf_token(self, session_public: str) -> str:
        return _b64(
            hmac.new(
                self._purpose_key("csrf-token"), session_public.encode(), hashlib.sha256
            ).digest()
        )

    def csrf_verifier(self, lookup: str, token: str) -> bytes:
        return self.verifier("csrf", lookup, token)

    def rate_limit_identifier(self, identifier: str) -> str:
        digest = hmac.new(
            self._purpose_key("rate-limit"), identifier.encode(), hashlib.sha256
        ).digest()
        return _b64(digest[:18])

    def _purpose_key(self, purpose: str) -> bytes:
        return hmac.new(self._master_key, f"renzai:{purpose}:v1".encode(), hashlib.sha256).digest()

    @staticmethod
    def _parts(value: str) -> tuple[str, str] | None:
        match = _CREDENTIAL_PATTERN.fullmatch(value)
        return (match.group(1), match.group(2)) if match is not None else None
