# Testing and verification

Phase 16 adds focused tests for demo isolation/idempotency, generated demo environment safety,
Attack Lab category/control coverage, reference-app safe/blocked/redaction-failure paths, and
OpenAPI auth documentation. These tests and the gates below were run on the uncommitted Phase 16
working tree against the committed Phase 15B baseline.

## Fresh local gates

| Area | Result |
| --- | --- |
| Backend static checks | Ruff check passed; Ruff format check: 445 files; strict mypy: 122 source files. |
| Backend regression | Full `pytest -q`: 288 passed, 10 skipped (live-service markers were run separately), 1 upstream Starlette/httpx deprecation warning. |
| Focused Phase 16/security-engine tests | 11 passed, including the persistence-failure test double and redaction fail-closed regression. |
| Frontend | Prettier, ESLint, TypeScript, 22 Vitest tests, and production build passed. |
| Python SDK | Ruff, formatting, mypy, 28 tests, and sdist/wheel build passed. |
| TypeScript SDK | Prettier, ESLint, typecheck, 24 tests, and build passed. |
| Live services | PostgreSQL 17.6 and Redis 8.2.1; fresh disposable PostgreSQL migration to `20261002_0007`, Alembic metadata check with no drift, 9 PostgreSQL integration tests, and 1 Redis integration test passed. |
| Compatibility | Phase 12 cross-SDK and Phase 14 frontend/backend compatibility scripts passed. |
| Compose | Demo override config passed; API/web/worker images built; migration gate, `/health`, `/ready`, Nginx, and `scripts/smoke_compose.py` passed on the local stack. |
| Demo | Live seed, duplicate seed, reset, duplicate reset, and reseed passed with the reserved synthetic tenant; unrelated owner identity remained. |
| Attack Lab | All 25 curated scenarios passed against the live Analyze API, covering 11 categories and benign controls. This is not a universal detection claim. |
| Reference app | Live safe and review/withheld paths passed with the local mock provider; unit regression also proves invalid redaction returns 502 without calling the provider. |
| Bruno collection | Bruno CLI 4.2.1 parsed the collection and generated standalone documentation to a temporary file; that file was removed. |
| Adoption assets | `scripts/verify_phase16_assets.py` passed local Markdown links, image paths, eight Mermaid blocks, Bruno structure, scenario schema/category/control coverage, required docs, and privacy markers. |
| Screenshots | Ten consistent synthetic screenshots were visually reviewed for personal data, credentials, and local paths. |
| Repository | `git diff --check` passed; historical migrations unchanged. |

The focused security-diff review of the original Phase 16 source snapshot completed with no
remaining reportable finding. Its snapshot predates the example-only redaction correction; the
current reference-app path was separately reviewed and regression-tested. A text/asset privacy scan
found no introduced personal identity, secret, or absolute local path in the adoption material.

These are local verification results, not production certification, an external penetration test,
or a promise of universal attack detection. The disposable verification database and port bridges
were removed after testing; the demo Compose stack and its named volumes were not deleted.
