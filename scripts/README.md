# Developer scripts boundary

Phase 4 keeps developer commands in the root `Makefile` and package scripts. Add platform-specific automation here only when it provides a verified, maintained command beyond those foundations.

`benchmark_phase7.py` measures the pure risk/policy path. `benchmark_phase8.py` measures the local message/analysis/response path with a deterministic mock provider. `benchmark_phase9.py` compares indexed incident list/detail queries with 100 and 1,000 rows. `benchmark_phase10.py` measures the full dashboard aggregate and PostgreSQL plan. `benchmark_phase11.py` measures context construction, redaction, result-schema validation, and local persistence while explicitly excluding provider/model latency. Run them with the repository virtual environment and `apps/api/src` on `PYTHONPATH`; results are local measurements, not a universal SLA. Database benchmarks require `RENZAI_TEST_DATABASE_URL` to name an explicitly disposable PostgreSQL database.

`verify_phase12_compatibility.py` starts an ephemeral local HTTP server and SQLite database, then
checks Python and built TypeScript SDK Analyze, safe Gateway configuration failure, and incident
read behavior. It uses only synthetic content and local test credentials and deletes its database
when complete. Build the TypeScript SDK before running it.
