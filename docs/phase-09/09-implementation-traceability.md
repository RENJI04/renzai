# Phase 9 implementation traceability

| Authority | Phase 9 evidence |
|---|---|
| FR-012; SEC-004; US-002–004 | Tenant predicates, composite ancestry constraints, hidden foreign IDs, role-matrix tests |
| FR-034; US-015 | Manual incident API and idempotent Gateway block/review creation |
| FR-035; US-015–017 | Incident snapshot, five statuses, assignee, comments, timeline, linked findings/action, queue/detail UI |
| FR-036; SEC-023; US-015–017 | Authorized assignment, comments, terminal classification, false-positive immutability, audit events |
| FR-041 | Incident core and UI require no optional AI provider |
| FR-045–046; P3-003; US-008, US-013 | Durable input/output analysis, fail-closed incident persistence, withheld provider content |
| FR-047; SEC-015, SEC-023; US-025 | Append-only audit records for manual/operator mutations and separate incident timeline |
| FR-051–053; SEC-010; US-011, US-020, US-026 | Privacy-aware detail and evidence-expired state with retained incident metadata |
| NFR-003, NFR-009; ADR-001, ADR-004 | Modular incident domain/application/API and PostgreSQL concurrency constraints |

Authoritative IDs come from Phase 1 requirements/user stories and Phase 3 traceability. This phase does not claim FR-039 analytics, FR-043 AI intelligence, FR-049–050/056 notifications or webhooks, or SDK work.
