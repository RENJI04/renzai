# Renzai v1.0 compatibility evidence

This matrix records tested boundaries, not blanket support for other versions.

| Component | Verified boundary | Scope |
| --- | --- | --- |
| API and worker Python | 3.13.16 on Alpine 3.23 in final candidate container images; 3.13 in CI | `pyproject.toml` requires Python >=3.13; local Phase 17A quality checks also ran on 3.14.2. |
| Python SDK | 3.11 and 3.13 in CI matrix | Package requires Python >=3.11; publication is separate from app v1.0.0. |
| Node.js | 22.23.2 in final candidate container images; Node 22 in CI | Frontend and TypeScript SDK tooling; local Phase 17A checks ran on 24.13.1. |
| pnpm | 11.19.0 | Frozen lockfile and explicit denied `unrs-resolver` build script. |
| PostgreSQL | 17.6-alpine | Empty upgrade, latest downgrade/re-upgrade, drift, and integration tests. |
| Redis | 8.2.1-alpine | Live integration tests and Compose readiness. |
| Docker / Compose | Docker Engine 29.6.1 / Compose 5.2.0 locally | Self-hosted local evaluation; not an OS-wide production guarantee. |
| Browser | Chromium via repository Playwright coverage where exercised | Responsive UI is tested; no formal cross-browser or WCAG certification. |
| Python SDK package | 0.1.0 | Local source distribution and wheel only; not on PyPI. |
| TypeScript SDK package | 0.1.0 | Local package archive only; not on npm. |

API protocol version, detector/risk schema versions, and SDK package versions are distinct from
the overall Renzai application release version `1.0.0`. See [SDK guidance](../sdk.md) and
[limitations](../limitations.md).
