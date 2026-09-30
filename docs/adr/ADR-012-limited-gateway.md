# ADR-012: Limited V1 gateway compatibility

**Status:** Accepted for Phase 2 architecture

## Context

Phase 1 OQ-009 fixes a bounded OpenAI-style compatibility target and defers streaming and advanced tool/function execution.

## Decision

Support non-streaming `POST /v1/chat/completions` with textual system/user/assistant messages, allowlisted common generation parameters and stable Renzai errors. Scan input before forwarding and output before return. Reject unsupported modes explicitly.

## Alternatives considered

Full protocol parity creates unreviewed output and tool enforcement paths. A proprietary gateway interface would increase client integration cost. Streaming can be reconsidered after safe incremental inspection contracts are designed and tested.

## Consequences

Some OpenAI-style clients need adaptation. Exact allowlist and error payloads are Phase 3 API contracts; documentation must not claim parity.

## Security implications

Unsupported tool execution is never silently forwarded. Inspection failure defaults to fail closed in staging/production; upstream provider failures do not bypass controls.

## Requirement references

OQ-004, OQ-009; FR-044–046; SEC-007, SEC-017; US-008, US-023.
