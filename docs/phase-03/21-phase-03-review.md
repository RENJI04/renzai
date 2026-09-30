# Phase 3 design review

**Status:** Contract-design package complete, subject to implementation-time verification. This review does not claim running software or executed tests. [Phase 1](../phase-01/12-phase-01-review.md) remains product authority; [Phase 2](../phase-02/18-phase-02-review.md) and its [16 ADRs](../phase-02/15-architecture-decisions.md) remain architecture authority. No Phase 4 work is included.

## Contract coverage

The package comprises 21 Markdown documents: [intake/decisions](01-phase-03-intake.md), [logical data model](02-logical-data-model.md), [37 entity/value-object contracts](03-entity-contracts.md), [auth/session](04-auth-session-contracts.md), [tenancy/RBAC](05-tenant-rbac-contracts.md), [API keys](06-application-api-key-contracts.md), [analysis/events](07-security-analysis-contracts.md), [detectors/findings](08-detector-finding-contracts.md), [numeric risk scoring](09-risk-scoring-specification.md), [policies](10-policy-contracts.md), [incidents/audit](11-incident-audit-contracts.md), [providers/outbound targets](12-provider-contracts.md), [Gateway wire behavior](13-gateway-api-contract.md), [privacy/retention](14-privacy-retention-contracts.md), [outbox/jobs](15-event-outbox-contracts.md), [webhooks/notifications](16-webhook-notification-contracts.md), [errors](17-error-contracts.md), [71 route/operation contracts](18-api-catalog.md), [configuration/limits](19-configuration-contracts.md), [traceability/vectors](20-phase-03-traceability.md), and this review. These counts include logical value objects and the `/health`, `/ready`, and Gateway operations; they do not imply tables or implemented routes.

The [logical ER diagram](02-logical-data-model.md) covers membership between users and organizations, application/environment/key ancestry, scoped policy/provider/webhook/audit roots, security events with finding/risk/policy snapshots, optional incident triggers, and notification/outbox delivery. Ten diagrams are Mermaid source across the package: ER, session lifecycle, key lifecycle, security analysis, policy evaluation, incident relationship, provider/Gateway flow, outbox state, webhook delivery, and retention flow. They are diagrams of proposed behavior, not runtime traces.

The API catalog covers auth; organizations/memberships; applications/environments/keys; Analyze and Playground; policies; incidents; logs/events; providers and optional AI analysis; notifications/webhooks; audit and analytics; health/readiness; and the limited Gateway. Each route row specifies purpose, authentication/role/scope, request/response, major errors, audit, rate class and idempotency. Shared conventions fix `snake_case` JSON, UUID/timestamp/enum representation, cursor pagination, bounded filters, CSRF/CORS and error envelope.

## Approved decisions and security consequences

| Decision | Resolved contract |
|---|---|
| P3-001 | A **valid** inspection with no enabled matching policy returns `allow`, null match and `no_policy_matched`, retaining findings/risk. Inspection failure is a separate error and fails closed in staging/production Gateway. |
| P3-002 | Priority is unique in effective organization/application/environment scope plus phase, including disabled non-archived policies; conflicting create/edit/enable/rollback is rejected. Per-scope first match plus safety-rank combination makes inheritance deterministic. |
| P3-003 | Analyze can return `require_review`; Gateway returns the stable `review_required` machine code for input or output, withholds forwarding or output, and durably triggers policy-specified incident/outbox intent without waiting for a reviewer. |
| P3-004 | Security content/events default to 30 days; audit defaults separately to 365 days and excludes raw prompt/response and credentials. Audit override has a bounded contract. |

Identity uses opaque server-side sessions with verifier-only storage, Secure/HttpOnly cookie, CSRF on browser writes, 30-minute idle/12-hour absolute defaults, rotation and revocation. Environment-scoped machine keys use `rz_<env>_<lookup>_<secret>` with random public lookup, 256-bit secret, keyed verifier, one-time display and immediate-revoke rotation. Neither identifier nor key lookup is authorization by itself. Provider credentials and webhook signing secrets are separately protected. SSRF controls validate normalized outbound targets and revalidate DNS/IP at connection time.

Risk uses a versioned deterministic 0–100 integer profile, explicit confidence arithmetic, overlap grouping, independent-category corroboration cap, critical-secret floor and fixed severity bands. Policy uses bounded facts/operators, immutable versions and explicit inheritance. Gateway supports only non-streaming textual chat completions with an allowlist of parameters; tools, streaming and arbitrary passthrough are rejected. Provider failure never relaxes security inspection.

## Data and privacy review

Every logical entity has an ID, tenant ownership or derivation, lifecycle, key attributes/relations, invariant, classification/retention, owner and reader/writer rule. Tenant-scoped reads combine server-derived organization context and object ancestry; workers revalidate scope, and relational constraints prevent cross-tenant references. PostgreSQL RLS is deferred as optional defense-in-depth, never the sole authorization layer. `FULL`, `REDACTED` (default) and `METADATA_ONLY` storage modes distinguish content from safe finding metadata; safe-content persistence defaults off. Logs, outbox, notifications, audit and analytics must not resurrect deleted raw content. Retention cleanup is tenant-scoped/idempotent and respects audit's separate clock.

## Traceability and consistency

The [matrix and design vectors](20-phase-03-traceability.md) cover all 56 FR, 16 NFR, 25 SEC and 32 US identifiers with inclusive ranges, linking each major V1 area to Phase 2 components/ADRs, concrete Phase 3 contracts and planned Phase 4 modules. Vectors specify login/session, cross-tenant hiding, key verification, provider-independent analysis, prompt injection, no-match allow, block/review, provider timeout, redaction, webhook signature and retention. They are not test results. The contract keeps Phase 1's product choices and Phase 2's 19-module boundary intact; Phase 3 adds only the four bounded approved decisions and detailed contracts.

## Remaining implementation-time choices

- Select concrete libraries/cipher suites and key-management deployment satisfying the separated key-purpose and rotation contracts; select the PostgreSQL UUIDv7 generator without changing ID semantics.
- Validate initial numeric risk weights/thresholds against a reviewed regression corpus, then activate an immutable profile version; do not silently change historical decisions.
- Benchmark payload, timeout, rate and latency defaults against the Phase 1 NFR environment; tune within documented ceilings and record new versions.
- Resolve physical schema/indexes, transaction/isolation choices, idempotency record TTL and worker lease tuning while preserving tenant and uniqueness invariants.
- Choose exact frontend rendering and provider-adapter details only when implementation begins; OpenAPI must reflect the actual limited surface.
- Decide production operational deployment of Redis, PostgreSQL, secret manager and telemetry within the Phase 2 topology; the contract defines readiness and fail-safe behavior, not infrastructure files.

## Validation record

Executed documentation checks found all 21 named files, 37 entity/value-object rows, 71 distinct API operations, ten Mermaid blocks that parse, and 259 local Markdown links across README and all documentation with no missing target. The trace table covers all FR-001–056, NFR-001–016, SEC-001–025 and US-001–032 IDs. P3-001 through P3-004 appear in the intake. The repository inventory contains Markdown only: no source, migration, SQL, Docker or CI artifact was created. No legacy project name or real credential was found. Our edits were confined to new Phase 3 Markdown and the README maturity/link text; Phase 1, Phase 2 and ADR files were not edited. This workspace is not a Git repository, so a Git diff/status cannot independently verify historical file state. No implementation or executable tests are claimed.
