# Architecture overview and Phase 1 intake

**Status:** Phase 2 design. This package describes a proposed V1 implementation; none of its components exists yet. [Phase 1](../phase-01/12-phase-01-review.md) remains the product authority. Requirement IDs below refer to its registers.

## Requirement intake

| Baseline | Confirmed V1 design constraint | Phase 1 source |
|---|---|---|
| Scope | Accounts, organizations/RBAC, applications/environments/keys, deterministic prompt/response analysis, versioned risk, policies, incidents, logs/dashboard/playground, optional provider intelligence, bounded gateway, audit, privacy/retention, notifications/webhooks, operational endpoints. | [Scope](../phase-01/02-scope.md), FR-001–056 |
| Deferred | V1.1 candidates: Slack/Discord/email alerts, richer reports, additional adapters, plugins, richer webhook management. V2 candidates: repository context, code/patch analysis, agent/tool enforcement, red-team engine, Kubernetes/distributed options. | [Scope](../phase-01/02-scope.md) |
| Architectural principles | Modular monolith with clear domain seams; direct analysis and gateway share one deterministic engine. Future extraction needs measured justification. | [Vision](../phase-01/01-product-vision.md), NFR-009 |
| Security | Server-side RBAC and tenant scoping; Argon2; no plaintext application keys; encrypted provider credentials; CSRF/CORS, validation, rate limits, safe errors and outbound URL controls. | SEC-001–025 |
| Privacy | Redacted content and 30-day retention by default; safe content is not persisted by default; full and metadata-only modes are opt-in; typed non-reversible placeholders. | OQ-003, OQ-007, OQ-010; FR-051–053 |
| Auth/session | Opaque server-side dashboard sessions, random Secure/HttpOnly cookie credential, CSRF on state changes. Scoped application API keys are separate. Browser JWT is not the V1 default. | OQ-001; FR-002, FR-015–019 |
| Gateway | Non-streaming `POST /v1/chat/completions`, textual system/user/assistant messages, allowlisted common parameters, stable Renzai errors. Streaming, advanced tool/function execution, and full protocol parity are deferred. | OQ-009; FR-044–046 |
| Failure behavior | Optional AI intelligence failure leaves deterministic core running. Invalid security inspection fails closed by default in staging/production; development may explicitly opt out. Provider forwarding failure gives a stable error without bypass. | OQ-004; FR-041, FR-046 |
| Risk | Integer 0–100, Low/Medium/High/Critical, confidence, explainable contributions, versioned deterministic profile, no hidden adaptive enforcement. | OQ-005; FR-029–030 |
| Outbound network | Remote HTTPS default; deny private/loopback/link-local/multicast/unspecified/metadata-style and URL credentials; validate DNS, each redirect and resolved IP; local exception needs explicit self-hosted opt-in. | OQ-006; SEC-020–021 |
| False positives | Incident classification never silently changes detectors. Corpus promotion is reviewed, version controlled, and separate from policy changes. | OQ-008; US-017 |
| Invitations | Time-bounded link works without SMTP; email delivery optional; token lifecycle controlled. | OQ-002; FR-009 |
| AI authority | Local deterministic detectors, heuristics, risk and policy remain the baseline authority. AI output is optional and distinctly labelled. | [Vision](../phase-01/01-product-vision.md), FR-041–043 |

No Phase 1 contradiction requiring a product decision was found. Numerical limits, scoring weights, supported generation-parameter names, and deployment-specific timeouts remain Phase 3 contract/configuration work; architecture here defines their owning boundaries and safe defaults, without changing product scope.

## V1 architectural choice

One FastAPI backend process model owns the domain modules and synchronous security decisions; Celery workers run the same application's asynchronous use cases. A Next.js web application provides the dashboard. PostgreSQL is the durable source of truth; Redis supports short-lived coordination and the task broker. Reverse proxy and observability components are deployment concerns, not domain services. See [ADR-001](../adr/ADR-001-modular-monolith.md).

This structure keeps request, policy, and tenant decisions inside one transactional codebase; avoids network hops in the analysis hot path; supports independent module tests; and can run multiple stateless API/worker replicas where the selected session/queue stores permit it. It also exposes module interfaces and data ownership for later evolution.

Service extraction in V2+ requires evidence: materially different scaling, isolation or deployment needs; worker-heavy processing that cannot be separated inside the monolith; sustained high-volume ingestion; or stable team ownership. An extraction proposal must quantify operational cost, consistency model, security boundary and test plan. No V1 domain module is an independent network service.

## Intended technology baseline

Web: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Recharts. Backend: Python, FastAPI, Pydantic, SQLAlchemy async, Alembic. Durable data: PostgreSQL. Short-lived coordination and task broker: Redis. Jobs: Celery. Security: Argon2, server-side sessions, API keys, encryption, RBAC. Deployment direction: Docker/Compose, Nginx, Linux primary. Telemetry direction: OpenTelemetry, Prometheus, Grafana. Testing direction: Pytest, Vitest, Playwright. These are design selections, not added dependencies or installations. Trade-offs are in [ADRs](15-architecture-decisions.md).

## Design map

| Concern | Primary document |
|---|---|
| Context, containers, modules | [02](02-system-context.md), [03](03-container-architecture.md), [04](04-domain-module-architecture.md) |
| Backend/front end | [05](05-backend-architecture.md), [06](06-frontend-architecture.md) |
| Detection, risk/policy, gateway | [07](07-security-engine-architecture.md), [08](08-risk-and-policy-architecture.md), [09](09-gateway-provider-architecture.md) |
| Identity, data flows, jobs | [10](10-auth-tenancy-security-architecture.md), [11](11-data-flow-and-trust-boundaries.md), [12](12-runtime-and-background-jobs.md) |
| Operations, decisions, threats, traceability | [13](13-observability-architecture.md)–[18](18-phase-02-review.md) |
