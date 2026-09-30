"""Runtime dependency lifecycle and readiness seam."""

from __future__ import annotations

from dataclasses import dataclass

from renzai.core.config import Settings
from renzai.db.session import Database
from renzai.infrastructure.crypto.application_keys import ApplicationKeyCrypto
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.infrastructure.crypto.provider_credentials import ProviderCredentialKeyRing
from renzai.infrastructure.http.openai_compatible import OpenAICompatibleProvider
from renzai.infrastructure.http.outbound import OutboundTargetGuard, PinnedHttpClient
from renzai.infrastructure.redis.client import RedisClient
from renzai.modules.auth.rate_limit import InMemoryAuthRateLimiter, RedisAuthRateLimiter
from renzai.modules.gateway.rate_limit import InMemoryGatewayRateLimiter, RedisGatewayRateLimiter
from renzai.modules.security.rate_limit import InMemoryAnalyzeRateLimiter, RedisAnalyzeRateLimiter


@dataclass(slots=True)
class RuntimeDependencies:
    settings: Settings
    database: Database
    redis: RedisClient
    identity_crypto: IdentityCrypto
    application_key_crypto: ApplicationKeyCrypto
    provider_credential_key_ring: ProviderCredentialKeyRing
    outbound_target_guard: OutboundTargetGuard
    chat_provider: OpenAICompatibleProvider
    auth_rate_limiter: InMemoryAuthRateLimiter | RedisAuthRateLimiter
    analyze_rate_limiter: InMemoryAnalyzeRateLimiter | RedisAnalyzeRateLimiter
    gateway_rate_limiter: InMemoryGatewayRateLimiter | RedisGatewayRateLimiter

    async def is_ready(self) -> bool:
        if not await self.database.ping():
            return False
        if self.settings.redis.required_for_readiness and not await self.redis.ping():
            return False
        return True

    async def close(self) -> None:
        await self.redis.close()
        await self.database.close()


def build_runtime_dependencies(settings: Settings) -> RuntimeDependencies:
    redis = RedisClient(settings.redis)
    provider_key_ring = ProviderCredentialKeyRing(
        settings.provider_crypto.active_key_id, settings.provider_crypto.keys
    )
    outbound_guard = OutboundTargetGuard(settings.outbound_network.trusted_local_provider_hosts)
    limiter: InMemoryAuthRateLimiter | RedisAuthRateLimiter
    analyze_limiter: InMemoryAnalyzeRateLimiter | RedisAnalyzeRateLimiter
    gateway_limiter: InMemoryGatewayRateLimiter | RedisGatewayRateLimiter
    if settings.app.environment.value == "test":
        limiter = InMemoryAuthRateLimiter(
            settings.identity.rate_limit_attempts, settings.identity.rate_limit_window_seconds
        )
        analyze_limiter = InMemoryAnalyzeRateLimiter(
            settings.analyze.rate_limit_requests, settings.analyze.rate_limit_window_seconds
        )
        gateway_limiter = InMemoryGatewayRateLimiter(
            settings.gateway.rate_limit_requests, settings.gateway.rate_limit_window_seconds
        )
    else:
        limiter = RedisAuthRateLimiter(
            redis,
            settings.identity.rate_limit_attempts,
            settings.identity.rate_limit_window_seconds,
        )
        analyze_limiter = RedisAnalyzeRateLimiter(
            redis,
            settings.analyze.rate_limit_requests,
            settings.analyze.rate_limit_window_seconds,
        )
        gateway_limiter = RedisGatewayRateLimiter(
            redis,
            settings.gateway.rate_limit_requests,
            settings.gateway.rate_limit_window_seconds,
        )
    return RuntimeDependencies(
        settings=settings,
        database=Database(settings.database),
        redis=redis,
        identity_crypto=IdentityCrypto(
            settings.session.verifier_key.get_secret_value(), settings.session.verifier_key_id
        ),
        application_key_crypto=ApplicationKeyCrypto(
            settings.application_keys.verifier_key.get_secret_value(),
            settings.application_keys.verifier_key_id,
        ),
        provider_credential_key_ring=provider_key_ring,
        outbound_target_guard=outbound_guard,
        chat_provider=OpenAICompatibleProvider(PinnedHttpClient(outbound_guard), provider_key_ring),
        auth_rate_limiter=limiter,
        analyze_rate_limiter=analyze_limiter,
        gateway_rate_limiter=gateway_limiter,
    )
