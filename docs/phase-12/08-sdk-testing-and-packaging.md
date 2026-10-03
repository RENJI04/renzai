# SDK testing and packaging

Unit tests use injected mock HTTP transports and make no external network requests. Shared safe
fixtures live in `tests/fixtures/sdk/` and cover Analyze success/block, Gateway block, review,
validation, rate limit, provider failure, incident pagination, analytics, and AI results.

Python checks:

```bash
python -m ruff check packages/python-sdk
python -m ruff format --check packages/python-sdk
python -m mypy --config-file packages/python-sdk/pyproject.toml
python -m pytest packages/python-sdk/tests
python -m build packages/python-sdk
```

TypeScript checks:

```bash
pnpm --dir packages/typescript-sdk format:check
pnpm --dir packages/typescript-sdk lint
pnpm --dir packages/typescript-sdk typecheck
pnpm --dir packages/typescript-sdk test
pnpm --dir packages/typescript-sdk build
pnpm --dir packages/typescript-sdk pack
```

Archive inspection verifies only intended runtime output, type declarations, package metadata, and
README are shipped. Neither package is published. The repository has no project license file at
this phase, so no SDK-specific license is invented; publication remains blocked pending project
licensing.

Compatibility uses the local Renzai FastAPI app, a local database, synthetic content, and test
credentials. It verifies Python Analyze, TypeScript Analyze, a safe Gateway error without a paid
provider, and an incident read.
