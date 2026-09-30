# ADR-007: Scoped application API keys

**Status:** Accepted for Phase 2 architecture

## Context

AI applications need non-browser credentials bound to an application environment. Phase 1 requires one-time display, prefix, last-used time, expiry, revocation and rotation.

## Decision

Use a visible non-secret lookup identifier/prefix plus a high-entropy secret. Store only a non-reversible/keyed verifier and scope metadata. Verify expiry/revocation and compare derived values in constant time where applicable. Keep these credentials separate from user sessions.

## Alternatives considered

Reusable plaintext database keys violate Phase 1. Reusing dashboard sessions for machine clients mixes trust boundaries. `rz_live_…`/`rz_test_…` are illustrative, not final formats.

## Consequences

The secret cannot be recovered after creation; rotation issues a replacement with a documented cutover. Last-used timestamp granularity must be honest.

## Security implications

Key theft grants scoped access until expiry/revocation. Key creation and lifecycle changes are authorized and audited; keys must never appear in logs.

## Requirement references

FR-015–019; NFR-006; SEC-002, SEC-011, SEC-018, SEC-024; US-006, US-027.
