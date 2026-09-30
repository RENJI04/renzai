# ADR-011: OpenAI-compatible provider abstraction

**Status:** Accepted for Phase 2 architecture

## Context

V1 supports optional remote or explicitly permitted local OpenAI-compatible providers for gateway forwarding and AI incident intelligence.

## Decision

Use a provider port for configuration validation, health check, chat forwarding, response normalization and error translation. Base URL/model/timeout are scoped configuration; credentials are encrypted at rest and available only inside the adapter.

## Alternatives considered

Hard-coding one vendor leaks protocol details into the security engine. Adding many provider-specific adapters in V1 broadens scope; richer adapters remain V1.1 candidates.

## Consequences

Compatibility is limited to the documented V1 gateway subset. Provider calls need bounded timeouts, secret handling and SSRF validation. Completion retry is avoided without an idempotency contract.

## Security implications

Provider output is untrusted and must be scanned. Private/local endpoint exceptions require explicit self-hosted opt-in; provider outages never disable deterministic core.

## Requirement references

FR-041–046; NFR-002, NFR-006, NFR-015; SEC-012, SEC-020–021; US-021–024.
