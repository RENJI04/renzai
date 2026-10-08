# Security model

Renzai assumes user text, provider responses, imported identifiers, and AI-generated advice are
untrusted. Its authoritative security path is deterministic: bounded validation, normalization,
detectors, aggregation, versioned risk, and declarative policy.

## Trust boundaries

- Browser control-plane access uses an opaque `HttpOnly` session cookie. State-changing requests
  require same-origin validation and the exact `X-Renzai-CSRF` token returned by session bootstrap.
- Server-side application traffic uses environment-scoped Bearer API keys. Only verifier material is
  stored; the full key is returned once.
- Organization membership and RBAC guard every control-plane resource. Composite foreign keys and
  tenant predicates preserve isolation when records reference applications, environments, providers,
  incidents, or AI results.
- Provider and AI-provider credentials are encrypted with purpose-separated configured key rings and
  never returned by read APIs.
- Outbound provider access uses explicit scheme/host rules, fresh address validation, redirect denial,
  bounded timeouts, and response-size limits to reduce SSRF and resource-exhaustion risk.

## Fail-closed enforcement

Required inspection, persistence, rate limiting, or provider-selection failures do not silently allow
traffic. Gateway input decisions are durable before provider network I/O. Output block, review, and
invalid redaction withhold provider content and persist truthful outcomes. Redis-dependent
security-required limiter paths fail closed in staging/production.

## Privacy and observability

Applications select `FULL`, `REDACTED`, or `METADATA_ONLY` storage and a bounded retention period.
Safe-content persistence is independently controlled. Logs, metrics, and traces exclude raw prompt,
response, credential, token, and session values; operators still own downstream telemetry access and
retention.

## Advisory AI boundary

AI Intelligence is optional, asynchronous, configuration- and consent-gated, and schema-validated.
It consumes a bounded incident context and produces labelled advisory content with provenance. It
cannot change deterministic findings, risk scores, policy decisions, incident authority, or Gateway
enforcement.

See [claims and non-claims](claims-and-non-claims.md), the [threat catalog](threat-catalog.md), and
[Phase 13 hardening](../phase-13/10-phase-13-review.md).
