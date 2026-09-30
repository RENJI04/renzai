# Observability architecture

OpenTelemetry instrumentation is intended for API, gateway, security engine, provider adapter and worker. Prometheus collects operational metrics; Grafana presents dashboards. Product security logs and audit events remain distinct from operational telemetry. None of these tools is installed in Phase 2.

## Signal design

| Signal | Example fields/measurements | Privacy rule |
|---|---|---|
| Structured logs | Timestamp, level, component, safe error code, correlation/request ID, organization ID or pseudonymous tenant label, detector/profile/policy version | No raw prompt/response, session/key/provider credentials, URL credentials or sensitive evidence. |
| Metrics | Request count, analysis/detector/provider latency, risk distribution, blocked requests, provider failures, worker queue depth, webhook failures, outbox lag, retention failures | Low-cardinality dimensions; no prompt content, user IDs or arbitrary URL labels. |
| Traces | Bounded spans for auth, analysis, risk, policy, provider forwarding and queued jobs | Propagate correlation ID, safe operation names; suppress raw bodies, secrets and full target URLs. |
| Product records | Privacy-filtered security events and append-only audit | Module-owned, tenant-scoped, governed by storage and retention rules. |

The edge creates or validates a request ID; it flows through API use cases, outbox, Celery jobs and safe provider/webhook diagnostics. Untrusted inbound trace headers are not blindly accepted as authority. A provider error response is sanitized before becoming log text. Optional observability outage never turns an inspection failure into an allow decision. Alerting on inspection failures, provider errors, outbox lag, queue depth and cleanup failures is an operations plan, not an implemented feature.

Verification later should check end-to-end correlation, metric cardinality, privacy redaction, failure visibility and that logging/telemetry failure does not alter policy action.
