# Coverage, performance, and flakiness

Backend and Python SDK coverage use pytest-cov with branch measurement. Frontend and TypeScript SDK
coverage use Vitest V8. XML/JSON artifacts are generated under ignored `.reports/`; transient HTML
or package output is not committed. No arbitrary percentage gate is set because the suite includes
schema-only, framework wiring, and environment-specific branches. Security and decision-critical
uncovered lines receive priority in review.

Phase 10/13 benchmarks remain reference measurements, not SLAs. Phase 14 reruns Analyze,
normalization, policy, Gateway, incident listing, analytics, and AI-context measurements through the
existing benchmark scripts. A regression is considered material only when repeatable under the same
local workload and environment; one noisy sample is not a defect.

Flakiness review focuses on race timing, fixed ports, timezone, global cache/data, and broad waits.
Live-service tests use unique UUID rows and explicit cleanup. Local server verifiers allocate free
loopback ports. Domain time tests use explicit timestamps. Concurrency tests assert database state.
Frontend Query retry behavior is accommodated by deterministic fresh responses rather than longer
global timeouts.

The final integrated measurement produced:

| Surface | Statements | Branches | Lines | Functions |
| --- | ---: | ---: | ---: | ---: |
| Backend and worker | 90.27% | 67.83% | 90.27% | n/a |
| Frontend | 74.94% | 70.98% | 75.75% | 66.19% |
| Python SDK | 77% combined | included in combined result | 77% combined | n/a |
| TypeScript SDK | 77.32% | 65.80% | 78.68% | 81.35% |

The backend/worker measurement passed 270 tests with ten deliberately opt-in live-service tests
skipped; those ten tests passed separately against PostgreSQL and Redis. Coverage identifies useful
future depth in Redis adapter branches, provider administration, outbound HTTP failure variants,
frontend security-console interactions, and less common SDK methods. None hides an unverified
decision-critical contract because the live, E2E, or compatibility suites exercise those boundaries.

The local reference benchmarks completed without correctness failure. Representative medians were
5.53 microseconds for zero-finding risk, 192.08 microseconds for a 100-policy worst-case decision,
0.3693 milliseconds for the local Gateway path, 0.0983 milliseconds for incident listing over
1,000 rows, and 0.0202 milliseconds for AI-result schema validation. The adversarial maximum-size
Analyze, normalization, and Gateway inspection samples measured 37.3587, 65.0509, and 36.4264
milliseconds respectively. PostgreSQL analytics measured 97.67 milliseconds median over 1,000
analyses and 311.21 milliseconds over 10,000 analyses; `EXPLAIN ANALYZE` used the tenant/time and
event indexes. These are local regression observations, not production SLAs.

No retry-only pass, intermittent assertion, fixed-port collision, or race instability was observed.
