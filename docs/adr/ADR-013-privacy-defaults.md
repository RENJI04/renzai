# ADR-013: Privacy-preserving storage defaults

**Status:** Accepted for Phase 2 architecture

## Context

Phase 1 OQ-003, OQ-007 and OQ-010 approve redacted-content storage, 30-day retention, safe-content non-persistence and typed placeholders.

## Decision

Apply application storage policy before persistence. Default to redacted content, 30 days and no safe prompt/response content persistence. Full and metadata-only modes are explicit choices. Use typed non-reversible placeholders plus safe finding metadata; do not retain original values just to rebuild a display.

## Alternatives considered

Full-content default aids investigation but increases sensitive-data exposure and contradicts the approved baseline. Metadata-only default minimizes content but loses required incident detail for some teams.

## Consequences

Incident evidence may be incomplete; UI must say so. Retention cleanup and derived-data deletion need design. Audit retention needs a distinct governance decision before data modeling.

## Security implications

Redaction is imperfect and must be regression-tested. Provider forwarding may disclose content even when Renzai stores only redacted/metadata records; this must be visible to operators.

## Requirement references

OQ-003, OQ-007, OQ-010; FR-028, FR-037, FR-051–053; SEC-010, SEC-023; US-011, US-020, US-026.
