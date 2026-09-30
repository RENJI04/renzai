# ADR-008: Deterministic-first security pipeline

**Status:** Accepted for Phase 2 architecture

## Context

Phase 1 requires core security without an external LLM and explainable prompt/response decisions.

## Decision

Run bounded validation, normalization, versioned deterministic detectors, aggregation, risk and policy synchronously. Optional AI classification/analysis is separate, labelled and never the sole enforcement authority.

## Alternatives considered

An LLM-only classifier can recognize some novel attacks but is unavailable during outages, less reproducible and contradicts the product baseline. A single static rule without risk/policy layers would limit explainability and governance.

## Consequences

Detector versions, evidence and false-positive corpus need maintenance. The pipeline can miss attacks; risk/confidence must not imply certainty.

## Security implications

Invalid inspection is an explicit failure, not an empty finding. Staging/production gateway defaults to fail closed. Raw evidence is filtered before storage and telemetry.

## Requirement references

FR-020–030, FR-041, FR-045–046; NFR-001–002, NFR-010; SEC-007, SEC-010, SEC-025; US-007–014, US-022–023, US-028–029.
