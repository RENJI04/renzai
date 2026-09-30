# Phase 3 intake and approved decisions

**Status:** V1 contract design. [Phase 1](../phase-01/12-phase-01-review.md) controls product scope; [Phase 2](../phase-02/18-phase-02-review.md) and the [ADRs](../phase-02/15-architecture-decisions.md) control architecture. This package defines contracts only. No route, model, migration, detector, or deployment is implemented.

## Baseline intake

| Subject | Binding baseline | Source |
|---|---|---|
| V1 boundary | Accounts/tenants, applications/keys, deterministic prompt and response analysis, risk/policy, incidents, logs/dashboard/playground, optional AI intelligence, limited gateway, audit, notifications, webhooks, privacy and operational API. V1.1 alerts/adapters/plugins and V2 repository/agent/tool/Kubernetes capabilities remain deferred. | [Scope](../phase-01/02-scope.md) |
| Modules and data ownership | One FastAPI modular monolith with 19 internal modules; owning module writes, other modules use public interfaces. PostgreSQL is durable; Redis/Celery supports async work. | [Module architecture](../phase-02/04-domain-module-architecture.md), ADR-001/004/005 |
| Tenant hierarchy | User ↔ Membership ↔ Organization → Application → Environment → application key. Server-derived tenant context, query-level checks, worker revalidation; IDs are never authorization. | [Tenancy](../phase-02/10-auth-tenancy-security-architecture.md), SEC-004 |
| Human and machine auth | Dashboard: opaque server-side session, Secure/HttpOnly cookie, CSRF. AI clients: separate environment-scoped one-time-display keys with non-reversible verifiers. | OQ-001, ADR-006/007 |
| Privacy and retention | REDACTED content, 30-day security content/event retention, no safe-content persistence by default; FULL and METADATA_ONLY are explicit choices. Typed non-reversible placeholders. | OQ-003/007/010, ADR-013 |
| Security lifecycle | Bounded input → normalization → deterministic detectors → aggregation → versioned risk → bounded policy → action. Invalid inspection is not an empty finding set. | [Engine](../phase-02/07-security-engine-architecture.md), ADR-008 |
| Risk and policy | 0–100 score, severity/confidence and explainable contributions from immutable profile version; policy scope/phase/priority/version with five actions. No hidden learning. | OQ-005/008, ADR-009/010 |
| Gateway and provider | Only non-streaming textual `POST /v1/chat/completions` with allowlisted parameters. Optional OpenAI-compatible remote/local provider; provider outage never bypasses inspection. | OQ-004/009, ADR-011/012 |
| Outbound security | Remote HTTPS default, deny private/metadata targets and URL credentials; validate DNS, resolved IPs and redirects; local provider requires explicit self-hosted exception. | OQ-006, ADR-014 |
| Events and audit | PostgreSQL transactional outbox, at-least-once async delivery, idempotent consumers; append-only audit with safe metadata. | [Runtime](../phase-02/12-runtime-and-background-jobs.md), ADR-015 |

## Approved bounded Phase 3 decisions

| ID | Decision | Contract effect |
|---|---|---|
| **P3-001** | A successful inspection with no enabled matching policy returns `action=allow`, `policy_match=null`, deterministic findings/risk, and rationale `no_policy_matched`. This is distinct from `inspection_failure`. | [Policy](10-policy-contracts.md), [analysis](07-security-analysis-contracts.md) |
| **P3-002** | Priority is unique within the same effective scope and phase. Duplicate priorities are rejected, including on enable/edit/rollback; no implicit tie breaker. | [Policy](10-policy-contracts.md), [data constraints](02-logical-data-model.md) |
| **P3-003** | Analyze may return `require_review` as an action. Gateway `require_review` withholds forwarding (input) or provider output (output), returns one stable `review_required` response, and durably triggers incident/outbox intent according to the policy. It never waits for manual review. | [Gateway](13-gateway-api-contract.md), [incident](11-incident-audit-contracts.md) |
| **P3-004** | Security content/event retention defaults to 30 days. Append-only audit events default to 365 days, contain no raw prompt/response or secret material, and may have separately constrained configuration. | [Privacy](14-privacy-retention-contracts.md), [audit](11-incident-audit-contracts.md) |

These decisions resolve the bounded open points recorded in the Phase 2 review; they do not change Phase 1 or Phase 2 documents. Remaining implementation choices are listed in [review](21-phase-03-review.md).
