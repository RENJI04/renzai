# Test inventory and gaps

The Phase 13 baseline collected 262 backend/worker tests, 17 frontend tests, 28 Python SDK tests,
24 TypeScript SDK tests, and nine opt-in live-service tests. Phase 14 collects 280 backend/worker
tests, including 14 selected E2E cases, nine PostgreSQL cases, one comprehensive Redis case, and
five live concurrency cases. The frontend suite now has 20 tests.

| Area | Existing and Phase 14 evidence | Layers |
| --- | --- | --- |
| Foundation/config/errors | app, architecture, config, logging, public error matrix | unit, contract |
| Identity/sessions | register/login/logout, rotation, reset/change, CSRF/origin, expiry | API E2E, failure |
| Organizations/memberships | invitations, RBAC, audit, tenant hiding, last-owner lock | API, PostgreSQL concurrency |
| Applications/environments/API keys | lifecycle, rotation/revocation/expiry, tenant FKs, one-time reveal | API E2E, PostgreSQL |
| Detection/normalization | every V1 detector, positive/negative/boundary, Unicode/encoded corpus | unit, corpus, performance |
| Risk/policy | exact vectors, 0/100, thresholds, ordering, scope/priority/grammar/actions | unit, API, PostgreSQL race |
| Analyze | validation, privacy, limits, keys, rate limit, persistence, deterministic replay | API E2E, failure injection |
| Providers/Gateway | encrypted config, SSRF/framing, input/output enforcement and durability | unit, API E2E, local HTTP double |
| Incidents | automatic/manual workflows, comments, assignment, transitions, false positive | API E2E, PostgreSQL concurrency |
| Analytics | windows, zero buckets, filters, distinct/Gateway semantics, tenant scope | API, native PostgreSQL |
| AI intelligence | four tasks, privacy, schemas, provenance, isolation, idempotency | API E2E, failure, PostgreSQL |
| Workers | JSON-only config, ID-only task boundary, duplicate delivery, single claim/result | unit, PostgreSQL concurrency |
| Frontend | identity, dashboard, playground, incidents, AI, provider states, security headers | component, contract, local integration |
| Python SDK | sync/async, Analyze/Gateway/session, errors, retries, cancellation, pagination | unit, local compatibility |
| TypeScript SDK | Analyze/Gateway/session, AbortSignal, errors, validation, pagination | unit, local compatibility |
| Live services | migrations/drift, FKs/indexes/locks/cascades/analytics; all Redis limiters | PostgreSQL, Redis |

Material gaps closed in Phase 14 were explicit marker/selectors, live AI worker ownership/result
coverage, complete live Redis limiter/fail-closed/key-safety coverage, stable public error-matrix
coverage, deterministic full-pipeline replay, cross-SDK semantic comparison, frontend provider
loading/error/empty states, and accessible names/status semantics.

Accepted gaps are recorded in `09-defects-and-test-gap-register.md`; none are hidden by aggregate
test counts.
