# Contributing to Renzai

Thank you for helping improve an open-source AI security platform. Keep changes narrow, explainable,
tenant-safe, and covered at the layer where behavior lives.

## Development setup

Use Python 3.13+, Node.js 22+, pnpm 11+, and Docker with Compose v2 for live-service checks.

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
pnpm install --frozen-lockfile
```

On Windows invoke `.\.venv\Scripts\python`; on POSIX use `.venv/bin/python`. Read
[local development](docs/development/local-development.md), [configuration](docs/development/configuration.md),
and [testing](docs/development/testing.md). The repository contains `apps/api`, `apps/web`, `workers`,
typed SDKs under `packages`, examples, migrations, deployment infrastructure, and phase evidence.

## Working agreements

- Preserve module boundaries and frozen public contracts; propose contract changes explicitly.
- Format Python with Ruff and TypeScript/Markdown-supported files with the configured Prettier tasks.
- Add unit/regression coverage for behavior. Use live PostgreSQL/Redis tests for database or limiter
  semantics that SQLite/mocks cannot establish.
- Never edit historical migrations. Add a new migration only when an authorized schema change needs it.
- Keep SDK changes in sync across Python, TypeScript, examples, and compatibility verification.
- Documentation commands, routes, limits, and security claims must match current code.
- Avoid logging or committing prompt content, credentials, session/API-key values, personal data,
  `.env` files, local database files, coverage output, or build caches.

## Before opening a pull request

Run the checks relevant to your change, then the full gates when practical:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest
pnpm --dir apps/web format:check
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Also run both SDK suites/builds, `docker compose config`, `python scripts/verify_phase16_assets.py`,
and `git diff --check` when touched. UI changes need accessible keyboard/focus behavior and synthetic
screenshots. Security-sensitive changes should state trust-boundary, privacy, fail-closed, tenancy,
and migration implications.

Use focused commits and describe scope, evidence, limitations, and operator impact. Feature proposals
should start with the problem, affected contract, threat/privacy analysis, and smallest coherent V1
shape. Do not post vulnerability details in a public issue; follow [SECURITY.md](SECURITY.md).
