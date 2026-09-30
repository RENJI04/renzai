# Architecture decisions

Each ADR is **Accepted for Phase 2 architecture** and remains a design proposal until implementation. Phase 1 product decisions are authoritative; an ADR cannot reverse them. Alternatives describe trade-offs, not V1 scope additions.

| ADR | Decision | Main references |
|---|---|---|
| [ADR-001](../adr/ADR-001-modular-monolith.md) | Modular monolith | NFR-009 |
| [ADR-002](../adr/ADR-002-fastapi-python.md) | Python/FastAPI backend | FR-020, NFR-010 |
| [ADR-003](../adr/ADR-003-nextjs-typescript.md) | Next.js/TypeScript frontend | FR-039–040 |
| [ADR-004](../adr/ADR-004-postgresql.md) | PostgreSQL durable store | FR-047–053 |
| [ADR-005](../adr/ADR-005-redis-celery.md) | Redis/Celery async work | FR-049–050 |
| [ADR-006](../adr/ADR-006-opaque-sessions.md) | Opaque server-side sessions | OQ-001, SEC-005 |
| [ADR-007](../adr/ADR-007-application-api-keys.md) | Scoped application API keys | FR-015–019 |
| [ADR-008](../adr/ADR-008-deterministic-security.md) | Deterministic-first security | FR-020–030,041 |
| [ADR-009](../adr/ADR-009-versioned-risk.md) | Versioned risk profiles | OQ-005 |
| [ADR-010](../adr/ADR-010-declarative-policy.md) | Bounded declarative policy | FR-031–033 |
| [ADR-011](../adr/ADR-011-provider-abstraction.md) | OpenAI-compatible provider port | FR-042–043 |
| [ADR-012](../adr/ADR-012-limited-gateway.md) | Limited V1 gateway subset | OQ-009 |
| [ADR-013](../adr/ADR-013-privacy-defaults.md) | Redacted/30-day privacy defaults | OQ-003,007,010 |
| [ADR-014](../adr/ADR-014-ssrf-safe-outbound-networking.md) | Shared SSRF outbound guard | OQ-006, SEC-020 |
| [ADR-015](../adr/ADR-015-append-only-audit.md) | Append-only audit with outbox | FR-047–048 |
| [ADR-016](../adr/ADR-016-observability-stack.md) | OTel/Prometheus/Grafana direction | NFR-011 |

Open design details for Phase 3 are tracked in [review](18-phase-02-review.md). They concern bounded contracts and configuration values, not reversals of approved Phase 1 decisions.
