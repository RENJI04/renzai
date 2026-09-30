# ADR-010: Bounded declarative policy engine

**Status:** Accepted for Phase 2 architecture

## Context

V1 needs ordered conditions and five actions with deterministic, explainable enforcement.

## Decision

Use a bounded declarative condition model over validated analysis facts and tenant context. Policies have explicit scope, phase, enabled state, priority and version. Evaluation uses one snapshot and returns matched policy plus rationale.

## Alternatives considered

An arbitrary scripting language is flexible but increases injection, nondeterminism and support burden. Hard-coded global rules remove analyst control. Phase 3 must define tie precedence and default action before implementation.

## Consequences

The model is intentionally less expressive; new condition types require reviewed changes. Policy versioning and preview are needed for safe rollout.

## Security implications

Invalid configuration is rejected rather than treated as allow. Input block prevents forwarding; output block/redact prevents unsafe return. Changes are authorized and audited.

## Requirement references

FR-031–033, FR-045–046; SEC-004, SEC-014–015; US-012–014, US-023.
