# Authentication, errors, timeouts, and retries

Application clients send the exact `Authorization: Bearer <application key>` contract. Keys are
never placed in URLs, logs, errors, `repr`, or `toString`. Tier 2 clients explicitly send an
existing Renzai session cookie; mutations additionally send `X-Renzai-CSRF`. AI generation accepts
the caller's `Idempotency-Key` without inventing or rotating one.

The SDK error hierarchy preserves the server's safe `code`, `message`, `request_id`, safe
`details`, and HTTP status. Stable mappings cover validation, authentication, authorization,
hidden/not-found, conflict/invalid transition, rate limit, policy block, review required,
inspection failure, configuration failure, provider failure, and provider timeout. Malformed
responses become `RenzaiProtocolError`; client network timeout and connection errors have separate
SDK errors. Raw bodies, stack traces, provider payloads, database messages, and credentials are not
attached.

Default network timeout is 30 seconds and is distinct from Renzai's server/provider timeouts.
Automatic retries are bounded to a maximum of five attempts and default to three. Only GET
connection failures, and GET `429` responses carrying numeric `Retry-After`, are retried. Analyze,
Gateway, AI generation, POST, and PATCH are never automatically retried. Backoff and maximum sleep
are bounded; there is no infinite retry path.
