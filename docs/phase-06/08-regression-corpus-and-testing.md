# Regression corpus and testing

The version-controlled JSON corpus is `apps/api/tests/corpus/v1_detection_corpus.json`. Its 24 cases comprise 8 positive, 7 negative, 4 adversarial, and 5 privacy cases. Each case names expected and optionally forbidden detector IDs without requiring an unnecessarily brittle exact finding list. Values are synthetic.

Focused unit tests cover every registered detector with positive, negative, and boundary inputs; deterministic ordering; Unicode/source maps; zero-width, escape, percent, entity, and Base64 candidates; invalid input; decode budgets; typed overlap redaction; required-detector failure; and key format/verification. API tests cover tenant isolation, uniqueness, archive/disable behavior, malformed/expired/revoked/rotated keys, one-time display, verifier-only storage, byte limits, privacy modes, safe-content default, Playground reuse, and limiter failure.

Performance instrumentation records normalization, detector, and total integer milliseconds. The benchmark-style test measures short, medium, and 32 KiB inputs with a generous 2-second regression ceiling; the product’s sub-100 ms simple-input number remains a measured target, not a universal SLA. Live PostgreSQL verifies migration round trips, composite tenant foreign keys, uniqueness, and event/finding persistence; live Redis verifies limiter state and rejection.

Final verification on 2026-09-26 used Python 3.14.2, PostgreSQL 18.6, and Redis 8.10.2. The full backend suite completed with 61 passing tests while both services were live. Alembic upgrade, schema drift check, downgrade to the Phase 5 revision, and re-upgrade all passed against PostgreSQL. The web application passed Prettier, ESLint, TypeScript, 6 Vitest tests, and the optimized Next.js production build.

The local deterministic-engine sample recorded these wall-clock distributions: short input (200 runs) median 0.055 ms, p95 0.072 ms, maximum 0.175 ms; medium input (100 runs) median 5.582 ms, p95 5.795 ms, maximum 6.117 ms; and maximum accepted 32 KiB input (30 runs) median 36.714 ms, p95 38.901 ms, maximum 39.069 ms. These measurements characterize this machine and are not an external-service SLA.
