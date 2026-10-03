# Configuration

`.env.example` contains placeholders only. `Settings` consumes `RENZAI_*` values with explicit aliases, validates production HTTPS and credentialed CORS, and exposes typed groups for APP, DATABASE, REDIS, SESSION, CRYPTO, CSRF, CORS, RATE_LIMIT, SECURITY_ENGINE, OUTBOUND_NETWORK, PROVIDER, CELERY, LOGGING, OBSERVABILITY, PRIVACY, RETENTION and FEATURE_FLAGS.

Identity defaults are a 30-minute idle session, 12-hour absolute session, 30-minute reset token, 24-hour verification token, seven-day invitation, five auth attempts per 15-minute fixed window, three password-reset attempts per hour, and 120 cookie-authenticated mutations per minute. Production/staging require a supplied verifier key and secure cookies. Local development uses `renzai_session`; protected environments use `__Host-renzai_session`. Tokens, passwords, cookie values, and raw rate-limit identifiers are never committed, persisted in cleartext, or logged.

Mutating JSON bodies are pre-bounded to 256 KiB by default (configuration hard ceiling 1 MiB).
Analyze and Playground use a lower 64-KiB request ceiling and retain the 32-KiB UTF-8 content
limit; Gateway uses the lower configured 96-KiB request ceiling. Security-sensitive request models
reject unknown fields.

Phase 8 adds a JSON provider-credential key ring with an active key ID. Each root must contain at least 32 UTF-8 bytes, roots must be distinct from one another and from session/application-key verifier roots, and staging/production reject development placeholders. The default provider bounds are 3-second connect, 30-second chat, 5-second health, 128-KiB response, and zero redirects. Remote providers require HTTPS; local/private destinations require the local provider kind and an exact host entry in `RENZAI_OUTBOUND_TRUSTED_LOCAL_PROVIDER_HOSTS`; wildcards, CIDRs, and URL-like values are rejected.

Production also rejects debug mode and exposed interactive API documentation. CORS entries must be
exact HTTP(S) origins without credentials, path, query, or fragment, and production origins must use
HTTPS. Redis-backed auth, password-reset, session-write, Analyze, and Gateway limiters fail closed
when the required increment is unavailable.

Gateway defaults are a 96-KiB request body, 32 messages, 64-KiB combined message text, 4,096 generated-token ceiling, and a separate 30-requests-per-minute application-key bucket. Redis keys contain only the existing keyed application-key identifier, never the full key. See [Phase 8 request contract](../phase-08/05-gateway-request-contract.md) and [outbound network controls](../phase-08/03-outbound-network-and-ssrf.md).
