# Typed configuration and operational limits

Configuration is startup validated, versioned where it affects decisions, and sourced from protected environment/secret-manager inputs in a later implementation. This document defines types and defaults, not a `.env`, deployment file or secret.

## Groups and classification

| Group | Contract examples | Class / startup rule |
|---|---|---|
| APP | public base URL, environment `development|staging|production`, trusted proxy set | INTERNAL; reject inconsistent HTTPS/proxy settings. |
| DATABASE | connection reference, pool/time limits | SECRET connection credential; required for readiness. |
| REDIS | broker/limiter endpoint and auth | SECRET connection credential; required for protected traffic by default. |
| SESSION | cookie origin/scope, 30-minute idle, 12-hour absolute, verifier key ID | SECRET verifier material; fail startup if absent. |
| CRYPTO | provider-encryption key ring and active key ID | SECRET; fail readiness if unable to decrypt active records. |
| CSRF | token verifier key/reference, allowed origin | SECRET key; same-origin default. |
| CORS | explicit origin allowlist | INTERNAL; default no cross-origin credentialed requests, never wildcard with credentials. |
| RATE_LIMIT | class limits below, shared limiter behavior | INTERNAL; invalid/absent critical limiter fails closed. |
| SECURITY_ENGINE | active ruleset/profile versions, detector budgets | INTERNAL; invalid profile/ruleset prevents readiness. |
| OUTBOUND_NETWORK | HTTPS/port policy, denied ranges, exact local exception allowlist | SENSITIVE; remote/private defaults enforced and versioned. |
| PROVIDER | default timeouts, response limit, permitted kinds | SENSITIVE; provider secrets separate encrypted records. |
| CELERY | broker/worker timeouts/retry ceilings | INTERNAL/SECRET broker auth; async degradation visible. |
| LOGGING | level, safe field allowlist, correlation behavior | INTERNAL; raw body logging forbidden. |
| OBSERVABILITY | collector/metric endpoints and safe labels | INTERNAL/SENSITIVE; telemetry failure does not change decisions. |
| PRIVACY | REDACTED default, safe-content persistence false | INTERNAL; unsafe override authorized/audited. |
| RETENTION | security 30 days; audit 365 days | INTERNAL; startup checks allowed ranges. |
| FEATURE_FLAGS | development-only less restrictive inspection behavior | SENSITIVE; absent means production/staging fail closed. |

Cryptographic purposes use separate key rings/IDs: provider-credential encryption, session/API-key verifier derivation, CSRF token verification where keyed, and per-destination webhook signing material. Never use one key for all purposes. Rotation marks a new active key while old encrypted/verifier records remain readable/valid only for a bounded migration window; revocation must not make active records unverifiable without a planned transition. No key is committed to the repository. Exact cipher/library and key-management deployment are implementation choices that must meet these lifecycle contracts.

## Initial configurable limits

| Limit | Proposed default | Hard safety ceiling / behavior |
|---|---:|---|
| General JSON body | 256 KiB | 1 MiB; endpoint-specific lower limit wins. |
| Analyze text | 32 KiB UTF-8 | 128 KiB; Analyze body ≤64 KiB default. |
| Gateway combined message text | 64 KiB UTF-8, ≤32 messages | 128 KiB; body ≤96 KiB default. |
| Provider output body | 128 KiB | 512 KiB; excess is `provider_error`, never unchecked return. |
| Webhook response body | 8 KiB | 32 KiB; ignored beyond safe diagnostics. |
| Pagination | default 50, max 100 | 200 hard ceiling; stable cursor order. |
| Provider connect/total/health | 3s / 30s / 5s | 10s / 120s / 15s. |
| Security-event retention | 30 days | 7/30/90/custom, custom 1–365 days with authorized override. |
| Audit retention | 365 days | Configurable 90–3650 days, separately authorized. |

Limits count UTF-8 bytes after decoding where specified; the proxy and API both enforce body ceilings. Detection budgets and memory ceilings must be benchmarked against the NFR-001 target under a documented environment; the 100 ms simple-text target is not an unconditional SLA.

## Rate-limit classes

| Class | Initial default | Key and failure fallback |
|---|---|---|
| AUTH_STRICT | 5 attempts / 15 min | Account-normalized email + source; limiter unavailable → deny new login safely. |
| PASSWORD_RESET | 3 / hour | Account + source; generic response; unavailable → deny issuance safely. |
| SESSION | 120 / min | User/session; unavailable → protect writes with conservative deny. |
| ANALYZE | 60 / min | Application key + source; unavailable → 503, no analysis bypass. |
| GATEWAY | 30 / min | Application key + source; unavailable → 503, no provider forwarding. |
| ADMIN | 30 / min | User + organization; unavailable → deny sensitive mutation. |
| WEBHOOK_TEST | 3 / hour | Organization + destination; unavailable → deny test send. |

These are conservative starting values, configurable within operator-reviewed ceilings; they are not universal capacity promises. Redis/shared limiter failure does not convert a rejected/undecidable request to allow. `/health` remains 200 if the process is alive. `/ready` is 200 only when configuration, PostgreSQL, crypto material and security engine are valid and required shared rate limiting works. With Redis down, protected Analyze/Gateway/auth/admin writes are unavailable and `/ready` returns 503; read-only dashboard paths may still function, while async jobs queue in PostgreSQL outbox for later dispatch. Do not disclose which internal dependency failed in public readiness body.

## API and OpenAPI rules

Renzai application APIs use `/api/v1/`; Gateway uses `/v1/chat/completions`. JSON is `snake_case`; IDs are lowercase UUID strings, except opaque token/key strings; timestamps are UTC RFC 3339; enum values are lowercase `snake_case`. Required fields cannot be null; nullable fields are explicitly documented; omitted optional fields use documented defaults. Unknown request fields are rejected on security-sensitive contracts, including Gateway. Lists use cursor pagination: `limit` default 50/max 100, opaque cursor bound to tenant/filter/order, ordering by `(created_at DESC, id DESC)` unless specified. Filters are named allowlisted fields, no SQL-like expressions. OpenAPI will describe actual implemented contracts and the common error envelope.

## Frontend contract dependencies

`/auth/session` bootstraps user/CSRF; organization list and membership roles support switcher; application/environment lists support selector; analytics and event filters feed dashboard/logs; incident detail/timeline support triage; policy/version endpoints support editor/preview; session-authenticated Playground shares Analyze result; provider reads mask credentials; notification list/read and audit list support governance; key creation returns secret once. Backend remains authoritative for every UI action.
