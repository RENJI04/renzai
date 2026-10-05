# Testing and operational verification

Static verification runs Ruff, Ruff format check, mypy, backend tests, frontend Prettier/ESLint/TypeScript/Vitest/build, both SDK suites/builds, compatibility checks, Compose model validation, dashboard JSON parsing, environment-validation tests, and `git diff --check`.

Live verification builds the API, worker, and web images; starts the Compose stack with disposable named volumes; verifies migrations, PostgreSQL, Redis, API liveness/readiness, frontend/proxy/session routing, worker ping, metrics, Prometheus targets, Collector startup, and Grafana health/provisioning. `scripts/smoke_compose.py` is non-destructive and uses no product data.

The final live gate passed on 2026-10-06 (Asia/Shanghai) using Docker Engine 29.6.1 / Docker Desktop 4.81.0. The runtime used PostgreSQL 17.6, Redis 8.2.1, Prometheus 3.6.0, OpenTelemetry Collector 0.138.0, and Grafana 12.2.0. All three Renzai images were rebuilt from the final working tree before startup.

Verified live results:

- The migration service completed successfully and Alembic reported `20261002_0007 (head)`. A separately created disposable database migrated from empty to head.
- The opt-in PostgreSQL suite passed 9 tests and the opt-in Redis suite passed 1 test against the Compose services.
- `/health`, `/ready`, the production frontend, Nginx routing, registration/login/session bootstrap, rejection of a missing CSRF token, and acceptance of the same mutation with the valid CSRF token all behaved as contracted.
- Celery answered control ping and executed the diagnostic request-correlation task through Redis with the expected result.
- API and worker metric endpoints emitted their Renzai series. Prometheus reported all six configured targets up: API, worker, PostgreSQL exporter, Redis exporter, OpenTelemetry Collector, and Prometheus. The exporters reported `pg_up 1` and `redis_up 1`.
- The collector accepted OTLP/HTTP spans from the instrumented services. Its basic debug exporter emitted only aggregate batch counts during the exposure check.
- Grafana started on its loopback management binding, provisioned the Prometheus datasource, and loaded the `Renzai Platform Overview` dashboard.
- PostgreSQL and Redis retained disposable verification state across safe service restarts; the migration gate, readiness, worker ping, and `scripts/smoke_compose.py --observability` passed again afterward.

Live startup exposed four operational defects, each fixed narrowly with regression assertions: the Nginx request-ID regex required quoting; the Celery health probe needed a 15-second container timeout; Prometheus 3.6 rejects a false value for its enable-only lifecycle flag, so the flag was removed and the safe default retained; and Grafana required a separate management network for an effective loopback port publication. No application contract or historical migration changed.

The final security recheck confirmed bounded metric labels, Nginx replacement of untrusted forwarded-client headers, absence of application secrets from Grafana and product-image configuration/history, and allowlist-only trace export. A malicious marker was absent from Prometheus labels and collector output. Only Nginx and Grafana published loopback host ports; no container mounted the Docker socket. The sealed final security-diff review reported no findings.

Final regression results were: Ruff and Ruff format clean; strict mypy clean across 121 source files; backend `278 passed, 10 skipped`; frontend `22 passed` plus production build; Python SDK `28 passed` plus sdist/wheel build; TypeScript SDK `24 passed` plus build; frontend/backend and cross-SDK compatibility checks passed; deployment configuration and Phase 15B asset verification passed; and `git diff --check` passed. The 10 default-skipped tests are precisely the live PostgreSQL/Redis tests that passed separately above.

Observability overhead measurements compare equivalent local HTTP requests with metrics disabled and enabled, plus deterministic Analyze/Gateway inspection paths with and without counter updates. These microbenchmarks exclude authentication, persistence, Redis, provider network I/O, and external exporter latency; results are local observations, not SLAs. External OTLP exporter latency is intentionally not placed on the synchronous request path because batch export is used.

On the 2026-10-05 Windows development host, the 500-request TestClient `/health` mean was 4.2208 ms with metrics disabled versus 4.5225 ms enabled (+0.3017 ms, +7.15%). The 1,000-iteration deterministic Analyze median changed from 0.1320 to 0.1358 ms (+0.0038 ms) with a counter update. The Gateway input/output inspection median was 0.3795 versus 0.3721 ms; the negative delta is timing noise, not evidence of a speedup. These do not validate production network or database latency.

This evidence validates the repository-controlled local stack and regression surface. It does not certify a production deployment, external TLS termination, operator secret management, backup recovery objectives, public-ingress policy, capacity, or availability targets.
