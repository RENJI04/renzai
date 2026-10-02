# Analytics testing and performance

Deterministic API tests cover exact summary counts, 10/4 threat rate, zero denominator, one Gateway request versus its two analyses, risk/action distributions, duplicate-category finding versus distinct-analysis counts, every persisted provider outcome, all incident states, all reader roles, hidden foreign filters, inclusive time boundaries, tenant scoping, and zero-filled buckets.

The live PostgreSQL integration test covers native UTC bucketing, `COUNT DISTINCT`, grouping, application/environment filtering, provider aggregation, and a second tenant excluded from every result. Migration verification covers upgrade, drift, downgrade to `20261001_0005`, re-upgrade, and final drift.

`scripts/benchmark_phase10.py` creates disposable 1,000- and 10,000-analysis datasets, measures 12 warmed full-dashboard queries per size, prints median/p95, and emits `EXPLAIN (ANALYZE, BUFFERS)` for the core completed-analysis count. Measurements are machine-local observations, not a contractual SLA. The Phase 10 review records the observed figures and query plan.
