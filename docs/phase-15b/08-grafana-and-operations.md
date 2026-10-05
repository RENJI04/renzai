# Grafana and operations

The optional Grafana service provisions an internal Prometheus datasource and the repository-controlled **Renzai Platform Overview** dashboard. Panels show request rate, p95 API latency, 5xx rate, Analyze decisions, Gateway outcomes, incident creation, worker task status, PostgreSQL health, Redis health, and API readiness. No synthetic security score or fabricated data is used.

Grafana requires an environment-supplied administrator password and disables sign-up, update checks, and analytics reporting in the supplied configuration. It is loopback-bound by default and is not routed through Renzai Nginx. Production operators should integrate approved authentication and ingress controls before remote exposure.

Prometheus retention is 15 days in the baseline. Dashboard and metric availability are diagnostic conveniences; their loss does not change deterministic enforcement or readiness.
