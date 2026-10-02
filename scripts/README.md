# Developer scripts boundary

Phase 4 keeps developer commands in the root `Makefile` and package scripts. Add platform-specific automation here only when it provides a verified, maintained command beyond those foundations.

`benchmark_phase7.py` measures the pure risk/policy path. `benchmark_phase8.py` measures the local message/analysis/response path with a deterministic mock provider. `benchmark_phase9.py` compares indexed incident list/detail queries with 100 and 1,000 rows. `benchmark_phase10.py` measures the full 90-day dashboard aggregate at 1,000 and 10,000 completed analyses and prints the core PostgreSQL query plan. Run them with the repository virtual environment and `apps/api/src` on `PYTHONPATH`; results are local measurements, not a universal SLA. Phase 10 requires `RENZAI_TEST_DATABASE_URL` to name an explicitly disposable PostgreSQL database.
