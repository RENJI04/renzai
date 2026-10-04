# Test strategy

The suite follows a test pyramid. Pure normalization, detection, risk, policy, parsing, and crypto
contracts stay at unit level. API/service collaborations use isolated SQLite databases. PostgreSQL,
Redis, row locking, partial indexes, native time bucketing, and concurrency use opt-in live tests.
Only a small set of representative cross-module workflows carries the `e2e` marker.

Markers are intentionally small:

| Marker | Purpose |
| --- | --- |
| `integration` | Requires an explicitly configured local service |
| `postgresql` | Disposable PostgreSQL behavior |
| `redis` | Disposable Redis behavior |
| `e2e` | Realistic public workflow crossing module boundaries |
| `concurrency` | Database-backed race/ownership invariant |
| `slow` | Intentionally broad or slower assurance test |

`scripts/run_phase14_tests.py` is the Windows/POSIX-compatible command entry point. Important
profiles are `fast`, `backend`, `frontend`, `python-sdk`, `typescript-sdk`, `e2e`, `postgresql`,
`redis`, `frontend-backend`, `compatibility`, `coverage`, and `release`. The release profile requires
the two explicit live-service URLs and never starts production services.

Generated JUnit and coverage artifacts go under ignored `.reports/`. No arbitrary percentage gate
is imposed. Coverage is reviewed for security and decision-critical gaps rather than optimized for a
headline number.

Tests must not depend on execution order, external internet, paid APIs, production data, global
leftovers, or fixed ports. Time-dependent domain tests use explicit timestamps or stored expiration
values; sleeps are limited to bounded readiness polling and deliberate concurrency overlap.
