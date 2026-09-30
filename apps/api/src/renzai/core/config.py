"""Typed, safe-by-default configuration for the Renzai foundation."""

from __future__ import annotations

from enum import StrEnum
from functools import cached_property
from typing import Self

from pydantic import AliasChoices, BaseModel, Field, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class PrivacyMode(StrEnum):
    FULL = "FULL"
    REDACTED = "REDACTED"
    METADATA_ONLY = "METADATA_ONLY"


class AppConfig(BaseModel):
    environment: Environment
    debug: bool
    public_base_url: HttpUrl
    trusted_proxies: tuple[str, ...]
    expose_docs: bool


class DatabaseConfig(BaseModel):
    url: str
    pool_size: int
    max_overflow: int


class RedisConfig(BaseModel):
    url: str
    required_for_readiness: bool


class LoggingConfig(BaseModel):
    level: str
    json_logs: bool


class CorsConfig(BaseModel):
    origins: tuple[str, ...]
    allow_credentials: bool


class PrivacyConfig(BaseModel):
    default_mode: PrivacyMode
    persist_safe_content: bool


class RetentionConfig(BaseModel):
    security_days: int
    audit_days: int


class SessionConfig(BaseModel):
    idle_minutes: int
    absolute_hours: int
    verifier_key: SecretStr
    verifier_key_id: str
    secure_cookie: bool


class IdentityConfig(BaseModel):
    password_reset_minutes: int
    email_verification_hours: int
    invitation_hours: int
    email_verification_required: bool
    rate_limit_attempts: int
    rate_limit_window_seconds: int


class ApplicationKeyConfig(BaseModel):
    verifier_key: SecretStr
    verifier_key_id: str
    maximum_expiry_days: int


class AnalyzeConfig(BaseModel):
    max_text_bytes: int
    hard_max_text_bytes: int
    rate_limit_requests: int
    rate_limit_window_seconds: int
    normalization_version: str
    ruleset_version: str


class ProviderCryptoConfig(BaseModel):
    active_key_id: str
    keys: dict[str, SecretStr]


class ProviderConfig(BaseModel):
    connect_timeout_seconds: int
    chat_timeout_seconds: int
    health_timeout_seconds: int
    response_max_bytes: int
    redirect_limit: int


class OutboundNetworkConfig(BaseModel):
    trusted_local_provider_hosts: tuple[str, ...]
    validation_policy_version: str


class GatewayConfig(BaseModel):
    max_body_bytes: int
    max_message_count: int
    max_combined_message_bytes: int
    max_tokens: int
    rate_limit_requests: int
    rate_limit_window_seconds: int


class FeatureFlagsConfig(BaseModel):
    unsafe_inspection_override: bool


class CeleryConfig(BaseModel):
    task_always_eager: bool
    task_time_limit_seconds: int = 60
    task_soft_time_limit_seconds: int = 45


class FoundationGroupConfig(BaseModel):
    """Typed marker for a Phase 3 group whose product-specific values are deferred."""

    configured: bool = False


class Settings(BaseSettings):
    """Settings sourced from `RENZAI_*` environment variables or a local `.env` file.

    Field aliases deliberately include the full environment-variable name so the public
    `.env.example` names remain stable without exposing a nested-settings implementation.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        validation_alias=AliasChoices("RENZAI_APP_ENVIRONMENT", "app_environment"),
    )
    app_debug: bool = Field(
        default=False, validation_alias=AliasChoices("RENZAI_APP_DEBUG", "app_debug")
    )
    app_public_base_url: HttpUrl = Field(
        default=HttpUrl("http://localhost:3000"),
        validation_alias=AliasChoices("RENZAI_APP_PUBLIC_BASE_URL", "app_public_base_url"),
    )
    app_trusted_proxies: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("RENZAI_APP_TRUSTED_PROXIES", "app_trusted_proxies"),
    )
    app_expose_docs: bool | None = Field(
        default=None, validation_alias=AliasChoices("RENZAI_APP_EXPOSE_DOCS", "app_expose_docs")
    )

    database_url: str = Field(
        default="postgresql+asyncpg://renzai:replace-me@localhost:5432/renzai",
        validation_alias=AliasChoices("RENZAI_DATABASE_URL", "database_url"),
    )
    database_pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        validation_alias=AliasChoices("RENZAI_DATABASE_POOL_SIZE", "database_pool_size"),
    )
    database_max_overflow: int = Field(
        default=5,
        ge=0,
        le=50,
        validation_alias=AliasChoices("RENZAI_DATABASE_MAX_OVERFLOW", "database_max_overflow"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("RENZAI_REDIS_URL", "redis_url"),
    )
    redis_required_for_readiness: bool | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "RENZAI_REDIS_REQUIRED_FOR_READINESS", "redis_required_for_readiness"
        ),
    )
    logging_level: str = Field(
        default="INFO", validation_alias=AliasChoices("RENZAI_LOGGING_LEVEL", "logging_level")
    )
    logging_json: bool | None = Field(
        default=None, validation_alias=AliasChoices("RENZAI_LOGGING_JSON", "logging_json")
    )
    cors_origins: tuple[str, ...] = Field(
        default=(), validation_alias=AliasChoices("RENZAI_CORS_ORIGINS", "cors_origins")
    )
    cors_allow_credentials: bool = Field(
        default=True,
        validation_alias=AliasChoices("RENZAI_CORS_ALLOW_CREDENTIALS", "cors_allow_credentials"),
    )
    privacy_default_mode: PrivacyMode = Field(
        default=PrivacyMode.REDACTED,
        validation_alias=AliasChoices("RENZAI_PRIVACY_DEFAULT_MODE", "privacy_default_mode"),
    )
    privacy_persist_safe_content: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RENZAI_PRIVACY_PERSIST_SAFE_CONTENT", "privacy_persist_safe_content"
        ),
    )
    retention_security_days: int = Field(
        default=30,
        ge=1,
        le=365,
        validation_alias=AliasChoices("RENZAI_RETENTION_SECURITY_DAYS", "retention_security_days"),
    )
    retention_audit_days: int = Field(
        default=365,
        ge=90,
        le=3650,
        validation_alias=AliasChoices("RENZAI_RETENTION_AUDIT_DAYS", "retention_audit_days"),
    )
    session_idle_minutes: int = Field(
        default=30,
        ge=1,
        validation_alias=AliasChoices("RENZAI_SESSION_IDLE_MINUTES", "session_idle_minutes"),
    )
    session_absolute_hours: int = Field(
        default=12,
        ge=1,
        validation_alias=AliasChoices("RENZAI_SESSION_ABSOLUTE_HOURS", "session_absolute_hours"),
    )
    session_verifier_key: SecretStr = Field(
        default=SecretStr("development-only-replace-this-32-byte-key"),
        min_length=32,
        validation_alias=AliasChoices("RENZAI_SESSION_VERIFIER_KEY", "session_verifier_key"),
    )
    session_verifier_key_id: str = Field(
        default="v1",
        validation_alias=AliasChoices("RENZAI_SESSION_VERIFIER_KEY_ID", "session_verifier_key_id"),
    )
    session_secure_cookie: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("RENZAI_SESSION_SECURE_COOKIE", "session_secure_cookie"),
    )
    password_reset_minutes: int = Field(
        default=30,
        ge=5,
        le=1440,
        validation_alias=AliasChoices("RENZAI_PASSWORD_RESET_MINUTES", "password_reset_minutes"),
    )
    email_verification_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        validation_alias=AliasChoices(
            "RENZAI_EMAIL_VERIFICATION_HOURS", "email_verification_hours"
        ),
    )
    invitation_hours: int = Field(
        default=168,
        ge=1,
        le=720,
        validation_alias=AliasChoices("RENZAI_INVITATION_HOURS", "invitation_hours"),
    )
    email_verification_required: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RENZAI_EMAIL_VERIFICATION_REQUIRED", "email_verification_required"
        ),
    )
    auth_rate_limit_attempts: int = Field(
        default=10,
        ge=1,
        le=1000,
        validation_alias=AliasChoices(
            "RENZAI_AUTH_RATE_LIMIT_ATTEMPTS", "auth_rate_limit_attempts"
        ),
    )
    auth_rate_limit_window_seconds: int = Field(
        default=300,
        ge=1,
        le=86400,
        validation_alias=AliasChoices(
            "RENZAI_AUTH_RATE_LIMIT_WINDOW_SECONDS", "auth_rate_limit_window_seconds"
        ),
    )
    application_key_verifier_key: SecretStr = Field(
        default=SecretStr("development-only-application-key-root"),
        min_length=32,
        validation_alias=AliasChoices(
            "RENZAI_APPLICATION_KEY_VERIFIER_KEY", "application_key_verifier_key"
        ),
    )
    application_key_verifier_key_id: str = Field(
        default="v1",
        validation_alias=AliasChoices(
            "RENZAI_APPLICATION_KEY_VERIFIER_KEY_ID", "application_key_verifier_key_id"
        ),
    )
    application_key_maximum_expiry_days: int = Field(
        default=365,
        ge=1,
        le=3650,
        validation_alias=AliasChoices(
            "RENZAI_APPLICATION_KEY_MAXIMUM_EXPIRY_DAYS",
            "application_key_maximum_expiry_days",
        ),
    )
    analyze_max_text_bytes: int = Field(
        default=32 * 1024,
        ge=1024,
        le=128 * 1024,
        validation_alias=AliasChoices("RENZAI_ANALYZE_MAX_TEXT_BYTES", "analyze_max_text_bytes"),
    )
    analyze_hard_max_text_bytes: int = Field(
        default=128 * 1024,
        ge=32 * 1024,
        le=128 * 1024,
        validation_alias=AliasChoices(
            "RENZAI_ANALYZE_HARD_MAX_TEXT_BYTES", "analyze_hard_max_text_bytes"
        ),
    )
    analyze_rate_limit_requests: int = Field(
        default=60,
        ge=1,
        le=10000,
        validation_alias=AliasChoices(
            "RENZAI_ANALYZE_RATE_LIMIT_REQUESTS", "analyze_rate_limit_requests"
        ),
    )
    analyze_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=86400,
        validation_alias=AliasChoices(
            "RENZAI_ANALYZE_RATE_LIMIT_WINDOW_SECONDS", "analyze_rate_limit_window_seconds"
        ),
    )
    provider_credential_active_key_id: str = Field(
        default="development-v1",
        validation_alias=AliasChoices(
            "RENZAI_PROVIDER_CREDENTIAL_ACTIVE_KEY_ID",
            "provider_credential_active_key_id",
        ),
    )
    provider_credential_keys: dict[str, SecretStr] = Field(
        default_factory=lambda: {
            "development-v1": SecretStr("development-only-provider-credential-root")
        },
        validation_alias=AliasChoices(
            "RENZAI_PROVIDER_CREDENTIAL_KEYS", "provider_credential_keys"
        ),
    )
    provider_connect_timeout_seconds: int = Field(
        default=3,
        ge=1,
        le=10,
        validation_alias=AliasChoices(
            "RENZAI_PROVIDER_CONNECT_TIMEOUT_SECONDS", "provider_connect_timeout_seconds"
        ),
    )
    provider_chat_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=120,
        validation_alias=AliasChoices(
            "RENZAI_PROVIDER_CHAT_TIMEOUT_SECONDS", "provider_chat_timeout_seconds"
        ),
    )
    provider_health_timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=15,
        validation_alias=AliasChoices(
            "RENZAI_PROVIDER_HEALTH_TIMEOUT_SECONDS", "provider_health_timeout_seconds"
        ),
    )
    provider_response_max_bytes: int = Field(
        default=128 * 1024,
        ge=1024,
        le=512 * 1024,
        validation_alias=AliasChoices(
            "RENZAI_PROVIDER_RESPONSE_MAX_BYTES", "provider_response_max_bytes"
        ),
    )
    provider_redirect_limit: int = Field(
        default=0,
        ge=0,
        le=2,
        validation_alias=AliasChoices("RENZAI_PROVIDER_REDIRECT_LIMIT", "provider_redirect_limit"),
    )
    outbound_trusted_local_provider_hosts: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "RENZAI_OUTBOUND_TRUSTED_LOCAL_PROVIDER_HOSTS",
            "outbound_trusted_local_provider_hosts",
        ),
    )
    gateway_max_body_bytes: int = Field(
        default=96 * 1024,
        ge=1024,
        le=1024 * 1024,
        validation_alias=AliasChoices("RENZAI_GATEWAY_MAX_BODY_BYTES", "gateway_max_body_bytes"),
    )
    gateway_max_message_count: int = Field(
        default=32,
        ge=1,
        le=32,
        validation_alias=AliasChoices(
            "RENZAI_GATEWAY_MAX_MESSAGE_COUNT", "gateway_max_message_count"
        ),
    )
    gateway_max_combined_message_bytes: int = Field(
        default=64 * 1024,
        ge=1024,
        le=128 * 1024,
        validation_alias=AliasChoices(
            "RENZAI_GATEWAY_MAX_COMBINED_MESSAGE_BYTES",
            "gateway_max_combined_message_bytes",
        ),
    )
    gateway_max_tokens: int = Field(
        default=4096,
        ge=1,
        le=4096,
        validation_alias=AliasChoices("RENZAI_GATEWAY_MAX_TOKENS", "gateway_max_tokens"),
    )
    gateway_rate_limit_requests: int = Field(
        default=30,
        ge=1,
        le=10000,
        validation_alias=AliasChoices(
            "RENZAI_GATEWAY_RATE_LIMIT_REQUESTS", "gateway_rate_limit_requests"
        ),
    )
    gateway_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=86400,
        validation_alias=AliasChoices(
            "RENZAI_GATEWAY_RATE_LIMIT_WINDOW_SECONDS", "gateway_rate_limit_window_seconds"
        ),
    )
    feature_flags_unsafe_inspection_override: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RENZAI_FEATURE_FLAGS_UNSAFE_INSPECTION_OVERRIDE",
            "feature_flags_unsafe_inspection_override",
        ),
    )
    celery_task_always_eager: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RENZAI_CELERY_TASK_ALWAYS_EAGER", "celery_task_always_eager"
        ),
    )

    @model_validator(mode="after")
    def validate_safe_defaults(self) -> Self:
        if self.session_absolute_hours * 60 < self.session_idle_minutes:
            raise ValueError("session absolute lifetime must be at least the idle lifetime")
        if self.cors_allow_credentials and "*" in self.cors_origins:
            raise ValueError("credentialed CORS cannot use a wildcard origin")
        if self.app_environment is Environment.PRODUCTION:
            if self.app_public_base_url.scheme != "https":
                raise ValueError("production public base URL must use HTTPS")
            if self.feature_flags_unsafe_inspection_override:
                raise ValueError("unsafe inspection override is development-only")
        if self.app_environment in {Environment.STAGING, Environment.PRODUCTION}:
            if self.session_verifier_key.get_secret_value().startswith("development-only"):
                raise ValueError("a non-development session verifier key is required")
            if self.session_secure_cookie is False:
                raise ValueError("secure session cookies are required outside local development")
            if self.application_key_verifier_key.get_secret_value().startswith("development-only"):
                raise ValueError("a non-development application-key verifier key is required")
        if self.application_key_verifier_key == self.session_verifier_key:
            raise ValueError("application-key and session verifier roots must be distinct")
        if self.provider_credential_active_key_id not in self.provider_credential_keys:
            raise ValueError("active provider credential key ID is missing from the key ring")
        if any(
            not key_id
            or len(key_id) > 80
            or any(ord(character) < 33 or ord(character) == 127 for character in key_id)
            for key_id in self.provider_credential_keys
        ):
            raise ValueError("provider credential key IDs must be bounded visible strings")
        provider_roots = {key.get_secret_value() for key in self.provider_credential_keys.values()}
        if any(len(value.encode("utf-8")) < 32 for value in provider_roots):
            raise ValueError("provider credential encryption roots must be at least 32 bytes")
        if len(provider_roots) != len(self.provider_credential_keys):
            raise ValueError("provider credential key-ring values must be distinct")
        if (
            self.session_verifier_key.get_secret_value() in provider_roots
            or self.application_key_verifier_key.get_secret_value() in provider_roots
        ):
            raise ValueError("provider encryption roots must be purpose-separated")
        if self.app_environment in {Environment.STAGING, Environment.PRODUCTION} and any(
            value.startswith("development-only") for value in provider_roots
        ):
            raise ValueError("a non-development provider credential key ring is required")
        if self.analyze_max_text_bytes > self.analyze_hard_max_text_bytes:
            raise ValueError("Analyze default text limit cannot exceed its hard ceiling")
        if self.gateway_max_combined_message_bytes > self.gateway_max_body_bytes:
            raise ValueError("Gateway message limit cannot exceed its body limit")
        return self

    @cached_property
    def app(self) -> AppConfig:
        return AppConfig(
            environment=self.app_environment,
            debug=self.app_debug,
            public_base_url=self.app_public_base_url,
            trusted_proxies=self.app_trusted_proxies,
            expose_docs=self.app_expose_docs
            if self.app_expose_docs is not None
            else self.app_environment is not Environment.PRODUCTION,
        )

    @cached_property
    def database(self) -> DatabaseConfig:
        return DatabaseConfig(
            url=self.database_url,
            pool_size=self.database_pool_size,
            max_overflow=self.database_max_overflow,
        )

    @cached_property
    def redis(self) -> RedisConfig:
        return RedisConfig(
            url=self.redis_url,
            required_for_readiness=self.redis_required_for_readiness
            if self.redis_required_for_readiness is not None
            else self.app_environment in {Environment.STAGING, Environment.PRODUCTION},
        )

    @cached_property
    def logging(self) -> LoggingConfig:
        return LoggingConfig(
            level=self.logging_level,
            json_logs=self.logging_json
            if self.logging_json is not None
            else self.app_environment is Environment.PRODUCTION,
        )

    @cached_property
    def cors(self) -> CorsConfig:
        return CorsConfig(origins=self.cors_origins, allow_credentials=self.cors_allow_credentials)

    @cached_property
    def privacy(self) -> PrivacyConfig:
        return PrivacyConfig(
            default_mode=self.privacy_default_mode,
            persist_safe_content=self.privacy_persist_safe_content,
        )

    @cached_property
    def retention(self) -> RetentionConfig:
        return RetentionConfig(
            security_days=self.retention_security_days, audit_days=self.retention_audit_days
        )

    @cached_property
    def session(self) -> SessionConfig:
        return SessionConfig(
            idle_minutes=self.session_idle_minutes,
            absolute_hours=self.session_absolute_hours,
            verifier_key=self.session_verifier_key,
            verifier_key_id=self.session_verifier_key_id,
            secure_cookie=self.session_secure_cookie
            if self.session_secure_cookie is not None
            else self.app_environment not in {Environment.DEVELOPMENT, Environment.TEST},
        )

    @cached_property
    def identity(self) -> IdentityConfig:
        return IdentityConfig(
            password_reset_minutes=self.password_reset_minutes,
            email_verification_hours=self.email_verification_hours,
            invitation_hours=self.invitation_hours,
            email_verification_required=self.email_verification_required,
            rate_limit_attempts=self.auth_rate_limit_attempts,
            rate_limit_window_seconds=self.auth_rate_limit_window_seconds,
        )

    @cached_property
    def application_keys(self) -> ApplicationKeyConfig:
        return ApplicationKeyConfig(
            verifier_key=self.application_key_verifier_key,
            verifier_key_id=self.application_key_verifier_key_id,
            maximum_expiry_days=self.application_key_maximum_expiry_days,
        )

    @cached_property
    def analyze(self) -> AnalyzeConfig:
        return AnalyzeConfig(
            max_text_bytes=self.analyze_max_text_bytes,
            hard_max_text_bytes=self.analyze_hard_max_text_bytes,
            rate_limit_requests=self.analyze_rate_limit_requests,
            rate_limit_window_seconds=self.analyze_rate_limit_window_seconds,
            normalization_version="1.0.0",
            ruleset_version="1.0.0",
        )

    @cached_property
    def feature_flags(self) -> FeatureFlagsConfig:
        return FeatureFlagsConfig(
            unsafe_inspection_override=self.feature_flags_unsafe_inspection_override
        )

    @cached_property
    def provider_crypto(self) -> ProviderCryptoConfig:
        return ProviderCryptoConfig(
            active_key_id=self.provider_credential_active_key_id,
            keys=self.provider_credential_keys,
        )

    @cached_property
    def provider(self) -> ProviderConfig:
        return ProviderConfig(
            connect_timeout_seconds=self.provider_connect_timeout_seconds,
            chat_timeout_seconds=self.provider_chat_timeout_seconds,
            health_timeout_seconds=self.provider_health_timeout_seconds,
            response_max_bytes=self.provider_response_max_bytes,
            redirect_limit=self.provider_redirect_limit,
        )

    @cached_property
    def outbound_network(self) -> OutboundNetworkConfig:
        return OutboundNetworkConfig(
            trusted_local_provider_hosts=self.outbound_trusted_local_provider_hosts,
            validation_policy_version="1.0.0",
        )

    @cached_property
    def gateway(self) -> GatewayConfig:
        return GatewayConfig(
            max_body_bytes=self.gateway_max_body_bytes,
            max_message_count=self.gateway_max_message_count,
            max_combined_message_bytes=self.gateway_max_combined_message_bytes,
            max_tokens=self.gateway_max_tokens,
            rate_limit_requests=self.gateway_rate_limit_requests,
            rate_limit_window_seconds=self.gateway_rate_limit_window_seconds,
        )

    @cached_property
    def celery(self) -> CeleryConfig:
        return CeleryConfig(
            task_always_eager=self.celery_task_always_eager
            or self.app_environment is Environment.TEST,
        )

    @cached_property
    def crypto(self) -> FoundationGroupConfig:
        return FoundationGroupConfig(configured=True)

    @cached_property
    def csrf(self) -> FoundationGroupConfig:
        return FoundationGroupConfig(configured=True)

    @cached_property
    def rate_limit(self) -> FoundationGroupConfig:
        return FoundationGroupConfig(configured=True)

    @cached_property
    def security_engine(self) -> FoundationGroupConfig:
        return FoundationGroupConfig(configured=True)

    @cached_property
    def observability(self) -> FoundationGroupConfig:
        return FoundationGroupConfig(configured=True)
