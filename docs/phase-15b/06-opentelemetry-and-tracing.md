# OpenTelemetry and tracing

Tracing is disabled by default. Set `RENZAI_OBSERVABILITY_TRACING_ENABLED=true` and a credential-free HTTP(S) `RENZAI_OBSERVABILITY_OTLP_TRACES_ENDPOINT` to enable sampled OTLP/HTTP export. The sample ratio is bounded between zero and one. The Compose observability profile provides an internal Collector endpoint.

Instrumentation covers FastAPI, SQLAlchemy, Redis, HTTPX, and Celery. Health, readiness, and metrics routes are excluded from inbound HTTP tracing. SQL comments are disabled. A final export allowlist replaces instrumentation span names with fixed operation classes, drops events and links, removes status descriptions, and retains only bounded methods, registered route templates, HTTP status, and SQL operation names. Raw URLs, query values, SQL statements, Redis keys, prompts, provider output, credentials, and tenant/user identifiers are not exported by this path.

The supplied Collector receives traces, batches them, and emits basic debug output for self-hosted verification; it is not durable trace storage. Operators can replace the exporter with an approved backend. Export failure must not bypass enforcement or make Prometheus/Grafana a core dependency.
