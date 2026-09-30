# ADR-009: Versioned deterministic risk profiles

**Status:** Accepted for Phase 2 architecture

## Context

Phase 1 OQ-005 requires explicit contributions, severity weighting, caps and combination rules, with profile version on every result and no hidden learning.

## Decision

Represent risk scoring as immutable reviewed profiles. A result records profile ID/version, detector versions, 0–100 score, severity, confidence and contribution breakdown. Rollout changes the selected profile rather than rewriting a used profile.

## Alternatives considered

Hard-coded weights are easy to start but difficult to explain/version. Adaptive online learning could shift enforcement silently and contradicts Phase 1.

## Consequences

Historical results remain interpretable. Profile changes require regression-corpus evaluation, audit and explicit rollout/rollback. Phase 3 determines exact weights and thresholds.

## Security implications

Transparent contributions support review but do not guarantee accuracy. Corpus promotion from false positives requires human approval and version control.

## Requirement references

OQ-005, OQ-008; FR-021, FR-029–030; SEC-025; US-007, US-009–010, US-017, US-028–029.
