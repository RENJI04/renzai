# Testing

The cross-platform Phase 14 entry point is `.venv/Scripts/python scripts/run_phase14_tests.py
<profile>` on Windows, or the equivalent virtual-environment Python on other platforms. Profiles
include `fast`, `backend`, `frontend`, `python-sdk`, `typescript-sdk`, `e2e`, `postgresql`, `redis`,
`frontend-backend`, `compatibility`, `coverage`, and `release`.

Backend checks are `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`,
and `python -m mypy`. Use `pytest -m e2e`, `-m postgresql`, `-m redis`, or `-m concurrency` for the
named assurance slices. Frontend checks are `pnpm --dir apps/web format:check`, `lint`, `typecheck`,
`test`, and `build`. Both SDKs have matching lint, format, type, test, coverage, and build commands.

Coverage output is generated beneath ignored `.reports/`. PostgreSQL and Redis tests require
explicit disposable `RENZAI_TEST_DATABASE_URL` and `RENZAI_TEST_REDIS_URL` values. Never point them
at production.

The Phase 5 suite additionally covers authentication, opaque credential verification, CSRF/origin
rejection, timeout and disabled-account handling, password-reset replay, verification replay,
organization isolation, invitation acceptance, RBAC, privilege freshness, audit creation, and
last-owner protection. Real PostgreSQL migration and concurrency evidence must be reported
separately from SQLite test results.
