"""Runtime dependency lifecycle and readiness seam."""

from __future__ import annotations

from dataclasses import dataclass

from renzai.core.config import Settings
from renzai.db.session import Database
from renzai.infrastructure.celery.ai_dispatcher import AITaskDispatcher
from renzai.infrastructure.crypto.ai_credentials import AICredentialKeyRing
from renzai.infrastructure.crypto.application_keys import ApplicationKeyCrypto
from renzai.infrastructure.crypto.identity import IdentityCrypto
from renzai.infrastructure.crypto.provider_credentials import ProviderCredentialKeyRing
from renzai.infrastructure.http.ai_openai_compatible import OpenAICompatibleAIIntelligenceProvider
from renzai.infrastructure.http.openai_compatible import OpenAICompatibleProvider
from renzai.infrastructure.http.outbound import OutboundTargetGuard, PinnedHttpClient
from renzai.infrastructure.redis.client import RedisClient
from renzai.modules.auth.rate_limit import (
    InMemoryAuthRateLimiter,
    RedisAuthRateLimiter,
    RedisSessionRateLimiter,
)
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
    ai_credential_key_ring: AICredentialKeyRing
    outbound_target_guard: OutboundTargetGuard
    chat_provider: OpenAICompatibleProvider
    ai_intelligence_provider: OpenAICompatibleAIIntelligenceProvider
    ai_task_dispatcher: AITaskDispatcher
    auth_rate_limiter: InMemoryAuthRateLimiter | RedisAuthRateLimiter
    password_reset_rate_limiter: InMemoryAuthRateLimiter | RedisAuthRateLimiter
    session_rate_limiter: InMemoryAuthRateLimiter | RedisSessionRateLimiter
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
    ai_key_ring = AICredentialKeyRing(
        settings.provider_crypto.active_key_id, settings.provider_crypto.keys
    )
    outbound_guard = OutboundTargetGuard(settings.outbound_network.trusted_local_provider_hosts)
    limiter: InMemoryAuthRateLimiter | RedisAuthRateLimiter
    reset_limiter: InMemoryAuthRateLimiter | RedisAuthRateLimiter
    session_limiter: InMemoryAuthRateLimiter | RedisSessionRateLimiter
    analyze_limiter: InMemoryAnalyzeRateLimiter | RedisAnalyzeRateLimiter
    gateway_limiter: InMemoryGatewayRateLimiter | RedisGatewayRateLimiter
    if settings.app.environment.value == "test":
        limiter = InMemoryAuthRateLimiter(
            settings.identity.rate_limit_attempts, settings.identity.rate_limit_window_seconds
        )
        reset_limiter = InMemoryAuthRateLimiter(
            settings.identity.password_reset_rate_limit_attempts,
            settings.identity.password_reset_rate_limit_window_seconds,
        )
        session_limiter = InMemoryAuthRateLimiter(
            settings.session.rate_limit_requests,
            settings.session.rate_limit_window_seconds,
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
        reset_limiter = RedisAuthRateLimiter(
            redis,
            settings.identity.password_reset_rate_limit_attempts,
            settings.identity.password_reset_rate_limit_window_seconds,
        )
        session_limiter = RedisSessionRateLimiter(
            redis,
            settings.session.rate_limit_requests,
            settings.session.rate_limit_window_seconds,
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
        ai_credential_key_ring=ai_key_ring,
        outbound_target_guard=outbound_guard,
        chat_provider=OpenAICompatibleProvider(PinnedHttpClient(outbound_guard), provider_key_ring),
        ai_intelligence_provider=OpenAICompatibleAIIntelligenceProvider(
            PinnedHttpClient(outbound_guard), ai_key_ring
        ),
        ai_task_dispatcher=AITaskDispatcher(
            settings.redis.url, eager=settings.celery.task_always_eager
        ),
        auth_rate_limiter=limiter,
        password_reset_rate_limiter=reset_limiter,
        session_rate_limiter=session_limiter,
        analyze_rate_limiter=analyze_limiter,
        gateway_rate_limiter=gateway_limiter,
    )
