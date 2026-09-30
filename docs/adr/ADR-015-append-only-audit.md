# ADR-015: Append-only audit with durable event intent

**Status:** Accepted for Phase 2 architecture

## Context

V1 requires accountable security changes and append-only correction semantics; async notifications must not be lost between DB commit and queue publish.

## Decision

Append audit records through one authorized port and correct by later event. Commit relevant state, audit and a PostgreSQL outbox intent in one transaction. Dispatch asynchronous consumers at least once with idempotency keys.

## Alternatives considered

Mutable audit rows erase history. Direct queue publish after commit can lose notifications; before commit can publish events for rolled-back changes. Cryptographic log chaining is a future tamper-evidence option, not a V1 claim.

## Consequences

An outbox dispatcher and backlog monitoring add operational work. Audit retention requires a separate documented decision. Event delivery is eventually consistent.

## Security implications

Restrict DB write permissions, tenant-scope audit reads, exclude raw secrets and preserve correlation IDs. Database administrators can still tamper absent additional controls.

## Requirement references

FR-047–050; SEC-015, SEC-019, SEC-023; US-025, US-030–031.
