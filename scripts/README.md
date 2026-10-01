# Developer scripts boundary

Phase 4 keeps developer commands in the root `Makefile` and package scripts. Add platform-specific automation here only when it provides a verified, maintained command beyond those foundations.

`benchmark_phase7.py` measures the pure risk/policy path. `benchmark_phase8.py` measures the local message/analysis/response path with a deterministic mock provider. `benchmark_phase9.py` compares indexed incident list/detail queries with 100 and 1,000 rows. Run them with the repository virtual environment and `apps/api/src` on `PYTHONPATH`; results are local measurements, not a universal SLA.
