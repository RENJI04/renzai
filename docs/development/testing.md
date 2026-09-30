# Testing

Backend checks are `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`, and `python -m mypy`. Frontend checks are `pnpm --dir apps/web lint`, `typecheck`, `test`, and `build`.

The Phase 5 suite additionally covers authentication, opaque credential verification, CSRF/origin rejection, timeout and disabled-account handling, password-reset replay, verification replay, organization isolation, invitation acceptance, RBAC, privilege freshness, audit creation, and last-owner protection. `RENZAI_TEST_DATABASE_URL` and `RENZAI_TEST_REDIS_URL` opt into live connectivity tests; never point them at production. Real PostgreSQL migration and concurrency evidence must be reported separately from SQLite test results.
