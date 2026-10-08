# Assurance and performance evidence

Phase 14 established backend, frontend, SDK, E2E, compatibility, concurrency, coverage, and local
performance evidence. Phase 15B then verified the complete Compose topology against live PostgreSQL
17.6 and Redis 8.2.1, including migrations, readiness, session/CSRF flow, Celery, metrics, traces,
Prometheus targets, exporters, Grafana provisioning, and safe persistence restarts.

The last committed Phase 15B regression inventory was: backend 278 passed with 10 live-service tests
skipped by default; frontend 22 passed plus production build; Python SDK 28 passed plus package build;
TypeScript SDK 24 passed plus build; Ruff, formatting, strict mypy, ESLint, TypeScript, compatibility,
deployment assets, and Compose smoke checks passed. Phase 16 adds demo/reset, Attack Lab, reference-app,
OpenAPI, collection, link, and privacy checks; current results are recorded in
[Phase 16 verification](phase-16/12-testing-and-verification.md).

## Local measurements

On the recorded Windows development host, 500 local TestClient `/health` requests averaged 4.2208 ms
with metrics disabled and 4.5225 ms enabled (+0.3017 ms). In 1,000 pure deterministic iterations,
Analyze median changed from 0.1320 to 0.1358 ms with counter update (+0.0038 ms); Gateway input/output
inspection measured 0.3795 versus 0.3721 ms, a negative timing delta treated as noise.

These microbenchmarks exclude production network, authentication, persistence, Redis, providers,
external telemetry, capacity, and failure conditions. They are local observations, not a production
SLA, certification, availability target, or capacity claim.
