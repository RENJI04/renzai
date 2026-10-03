from __future__ import annotations

import pytest
from pydantic import ValidationError

from renzai.core.config import Environment, PrivacyMode, Settings


def test_phase_three_secure_defaults_are_typed() -> None:
    settings = Settings(database_url="sqlite+aiosqlite://")
    assert settings.privacy.default_mode is PrivacyMode.REDACTED
    assert settings.privacy.persist_safe_content is False
    assert settings.retention.security_days == 30
    assert settings.retention.audit_days == 365
    assert settings.session.idle_minutes == 30
    assert settings.session.absolute_hours == 12
    assert settings.analyze.max_text_bytes == 32 * 1024
    assert settings.analyze.hard_max_text_bytes == 128 * 1024
    assert settings.provider.connect_timeout_seconds == 3
    assert settings.provider.chat_timeout_seconds == 30
    assert settings.provider.health_timeout_seconds == 5
    assert settings.provider.response_max_bytes == 128 * 1024
    assert settings.provider.redirect_limit == 0
    assert settings.gateway.max_body_bytes == 96 * 1024
    assert settings.gateway.max_message_count == 32
    assert settings.gateway.max_tokens == 4096
    assert (
        settings.application_keys.verifier_key.get_secret_value()
        != settings.session.verifier_key.get_secret_value()
    )


def test_production_rejects_http_and_unsafe_override() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_environment=Environment.PRODUCTION,
            app_public_base_url="http://renzai.example",
            database_url="postgresql+asyncpg://user:pass@db/renzai",
        )
    with pytest.raises(ValidationError):
        Settings(
            app_environment=Environment.PRODUCTION,
            app_public_base_url="https://renzai.example",
            database_url="postgresql+asyncpg://user:pass@db/renzai",
            feature_flags_unsafe_inspection_override=True,
        )
    with pytest.raises(ValidationError):
        Settings(
            app_environment=Environment.PRODUCTION,
            app_public_base_url="https://renzai.example",
            app_debug=True,
            database_url="postgresql+asyncpg://user:pass@db/renzai",
            session_verifier_key="production-session-verifier-root-0001",
            application_key_verifier_key="production-app-key-root-material-0001",
            provider_credential_keys={"production-v1": "production-provider-root-material-00001"},
            provider_credential_active_key_id="production-v1",
            session_secure_cookie=True,
        )
    with pytest.raises(ValidationError):
        Settings(
            app_environment=Environment.PRODUCTION,
            app_public_base_url="https://renzai.example",
            app_expose_docs=True,
            database_url="postgresql+asyncpg://user:pass@db/renzai",
            session_verifier_key="production-session-verifier-root-0001",
            application_key_verifier_key="production-app-key-root-material-0001",
            provider_credential_keys={"production-v1": "production-provider-root-material-00001"},
            provider_credential_active_key_id="production-v1",
            session_secure_cookie=True,
        )


def test_credentialed_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", cors_origins=("*",))


@pytest.mark.parametrize(
    "origin",
    [
        "https://user:password@example.com",
        "https://example.com/path",
        "https://example.com?query=true",
        "file:///tmp/renzai",
    ],
)
def test_cors_origins_must_be_exact_http_origins(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite://", cors_origins=(origin,))


@pytest.mark.parametrize("host", ["*", "0.0.0.0/0", "http://127.0.0.1", "bad host"])
def test_local_provider_allowlist_requires_exact_hosts(host: str) -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite+aiosqlite://",
            outbound_trusted_local_provider_hosts=(host,),
        )


def test_application_key_verifier_root_must_be_separate_and_secure_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite+aiosqlite://",
            application_key_verifier_key="development-only-replace-this-32-byte-key",
        )
    with pytest.raises(ValidationError):
        Settings(
            app_environment=Environment.PRODUCTION,
            app_public_base_url="https://renzai.example",
            database_url="postgresql+asyncpg://user:pass@db/renzai",
            session_verifier_key="production-session-verifier-root-0001",
            session_secure_cookie=True,
        )


def test_provider_credential_roots_are_separate_and_secure_outside_development() -> None:
    shared = "purpose-separated-root-material-0000000001"
    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite+aiosqlite://",
            provider_credential_active_key_id="provider-v1",
            provider_credential_keys={"provider-v1": shared},
            session_verifier_key=shared,
        )
    with pytest.raises(ValidationError):
        Settings(
            app_environment=Environment.STAGING,
            app_public_base_url="https://staging.renzai.example",
            database_url="postgresql+asyncpg://user:pass@db/renzai",
            session_verifier_key="staging-session-root-material-0000000001",
            application_key_verifier_key="staging-app-key-root-material-0000000001",
            session_secure_cookie=True,
        )
    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite+aiosqlite://",
            provider_credential_active_key_id="provider-v1",
            provider_credential_keys={"provider-v1": "short-root"},
        )
