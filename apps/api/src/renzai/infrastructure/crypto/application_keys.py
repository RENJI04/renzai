"""Purpose-isolated application API-key generation and verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass

ENVIRONMENT_TAGS = {"development": "dev", "staging": "stg", "production": "prd"}
_KEY_PATTERN = re.compile(r"\Arz_(dev|stg|prd)_([A-Za-z0-9_-]{22})_([A-Za-z0-9_-]{43})\Z")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass(frozen=True, slots=True)
class IssuedApplicationKey:
    public: str
    lookup: str
    prefix: str
    verifier: bytes
    environment_tag: str


@dataclass(frozen=True, slots=True)
class ParsedApplicationKey:
    environment_tag: str
    lookup: str
    secret: str


class ApplicationKeyCrypto:
    """Dedicated keyed verifier root; never shares session key material."""

    def __init__(self, verifier_key: str, key_id: str) -> None:
        self._verifier_key = verifier_key.encode("utf-8")
        self.key_id = key_id

    def issue(self, environment_type: str) -> IssuedApplicationKey:
        tag = ENVIRONMENT_TAGS[environment_type]
        lookup = _b64(secrets.token_bytes(16))
        secret = _b64(secrets.token_bytes(32))
        public = f"rz_{tag}_{lookup}_{secret}"
        return IssuedApplicationKey(
            public=public,
            lookup=lookup,
            prefix=f"rz_{tag}_{lookup[:8]}",
            verifier=self.verifier(lookup, secret),
            environment_tag=tag,
        )

    def parse(self, public: str) -> ParsedApplicationKey | None:
        match = _KEY_PATTERN.fullmatch(public)
        if match is None:
            return None
        return ParsedApplicationKey(match.group(1), match.group(2), match.group(3))

    def verify(self, public: str, expected_lookup: str, expected_verifier: bytes) -> bool:
        parsed = self.parse(public)
        if parsed is None:
            return False
        lookup_matches = hmac.compare_digest(parsed.lookup, expected_lookup)
        verifier_matches = hmac.compare_digest(
            self.verifier(parsed.lookup, parsed.secret), expected_verifier
        )
        return lookup_matches and verifier_matches

    def verifier(self, lookup: str, secret: str) -> bytes:
        return hmac.new(
            self._verifier_key,
            f"renzai:application-api-key:v1\0{lookup}\0{secret}".encode(),
            hashlib.sha256,
        ).digest()

    def rate_limit_identifier(self, key_id: str) -> str:
        return _b64(
            hmac.new(
                self._verifier_key,
                f"renzai:analyze-rate:v1\0{key_id}".encode(),
                hashlib.sha256,
            ).digest()[:18]
        )
