# Phase 13 scope and security baseline

Phase 13 hardens the committed Phase 12 implementation at baseline
`39ff2a31185caab3a3a5836836eda768e81e9ddd`. It adds no product capability, changes no frozen
migration, and does not begin Phase 14. The method was boundary-first: identify an abuse case,
confirm the existing control or reproduce the gap, make the smallest compatible correction, and
retain a regression test.

## Security-sensitive surface inventory

| Surface | Relevant attacker | Protected asset / authorization boundary | Fail-safe behavior and controls |
| --- | --- | --- | --- |
| Registration/login/reset/verification | Remote unauthenticated client | Account credentials and recovery | Explicit Argon2id profile, bounded passwords/tokens, one-time rows, keyed rate limits, safe errors |
| Sessions/cookies | Stolen or fixed credential | User identity and privilege version | Verifier-only storage, expiry/revocation, rotation, `HttpOnly`, `SameSite`, protected `__Host-` cookie |
| CSRF/CORS | Malicious site/browser context | Cookie-authenticated mutation | Session-bound token, exact Origin/Referer comparison, explicit origins, credentialed wildcard rejection |
| Organizations/memberships/RBAC | Low-privilege user or malicious tenant | Tenant membership and five-role authorization | Tenant-qualified queries, hidden not-found semantics, backend permission checks, last-owner locking |
| Application keys/Analyze | Leaked or malformed API key | Application/environment analysis scope | Random opaque secret, verifier-only storage, bounded parser/header, revocation/expiry, keyed limiter |
| Detection/risk/policy | Malicious content/configuration | Deterministic enforcement | Bounded normalization/candidates/grammar, allowlisted facts/operators/actions, fail-closed errors |
| Provider credentials | Tenant user or database reader | Gateway/AI API credentials | AES-256-GCM, random nonce, purpose/tenant/config AAD, key IDs, ciphertext-only persistence |
| Gateway/provider network | Malicious URL, DNS, provider, or response | Internal network and inspected content | HTTPS remote default, explicit local hosts, pinned validated addresses, no proxy/redirect, bounded response |
| Incidents/audit/analytics | Cross-tenant user or stored-XSS payload | Investigation history and aggregates | Tenant scope, optimistic versions, inert React text, bounded comments, append-style audit, privacy-safe aggregates |
| AI intelligence/workers | Prompt injection, stale permission, duplicate task | Incident data, credentials, provider cost | Advisory-only tasks, disclosure recheck, one owner/result, JSON ID-only messages, no task retry |
| Redis/Celery | Service outage or broker injection | Rate-limit and background-work integrity | Hashed bounded keys, fail-closed security limiters, JSON-only accepted content, known task payload |
| SDKs | Malicious consumer input/server response | API/session secrets and caller process | No redirects, bounded responses/retries, header/base-URL validation, secret-safe errors/logging |
| Frontend/API responses | Browser attacker/intermediary | Session data and rendered tenant content | React escaping, CSP/frame denial, nosniff/referrer policy, sensitive API `no-store` |
| Configuration/database | Operator mistake/concurrent request | Root secrets and tenant invariants | Protected-environment validation, composite FKs/uniques/checks, locks and optimistic concurrency |

An application cannot defend against a malicious host/root administrator. Deployment TLS, reverse
proxy trust, database/Redis network policy, root-key custody, backups, and host hardening remain
operator boundaries.

## Out of scope

No detector, risk formula, policy semantic, provider protocol, AI task, notification, webhook,
integration, billing, agent, streaming, or API-version feature was added. Phase 13 created no
database migration.
