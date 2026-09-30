# ADR-016: OpenTelemetry, Prometheus and Grafana direction

**Status:** Accepted for Phase 2 architecture

## Context

V1 requires structured logs, request IDs and metrics/tracing-ready design across API, gateway, detector, provider and worker paths.

## Decision

Instrument with OpenTelemetry; expose/collect safe metrics with Prometheus and visualize with Grafana. Keep product security records and audit separate from operational telemetry.

## Alternatives considered

Logs alone are simpler but weak for latency and queue behavior. A vendor-specific stack may offer faster setup but increases self-hosting dependence.

## Consequences

Collectors/dashboards add deployment and cardinality management. Operational telemetry outages do not change enforcement decisions.

## Security implications

No raw prompts, provider credentials, session/key values or full destination URLs in logs, metrics or spans; test sanitization and access restrictions.

## Requirement references

NFR-008, NFR-011–012; FR-037–039; SEC-010, SEC-017, SEC-023; US-018–019.
