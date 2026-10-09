# Final test matrix

This is a living Phase 17A verification record. It must not be interpreted as a public release
approval until all rows and the final review are complete.

| Gate | Candidate result |
| --- | --- |
| Ruff check, Ruff format, strict mypy | Passed on the candidate Python tree. |
| Backend pytest | Final combined live-service run: 300 passed; the OpenAPI, Quick Start, and Nginx DNS regressions passed. |
| PostgreSQL 17.6 | Fresh empty database upgrade to `20261002_0007`, drift check, downgrade to `20261002_0006`, re-upgrade, and final drift check passed; the configured PostgreSQL integration tests passed within the combined suite. |
| Redis 8.2.1 | 1/1 live integration test passed. |
| Frontend format/lint/type/test/build | Passed after Next.js 16.3.8 patch; 22/22 Vitest tests and production build passed. |
| Python SDK | Ruff/format/mypy, 28/28 tests, sdist, and wheel passed; LICENSE was included after the package rebuild. |
| TypeScript SDK | Format/lint/typecheck, 24/24 tests, and build passed. |
| Cross-SDK compatibility | Passed against a local test API. |
| E2E and frontend/backend compatibility | 14/14 backend E2E and 7/7 Playwright cases passed; frontend/backend compatibility passed. |
| Phase 16 asset and documentation links | Phase 16 and Phase 15B verifiers passed after final document updates. |
| Compose and clean-room | Source-only export built and started; migration, smoke, registration, seed, key, Analyze, incidents, 25/25 Attack Lab, and reference app passed. Post-base-update rebuild and unchanged-Nginx API/web recreation passed after dynamic-DNS fix; eight incidents persisted; clean shutdown passed. |
| Image scans and SBOM | Final API and worker images: five medium and zero high/critical findings each. Final web image: three medium and zero high/critical findings. Three final SPDX JSON SBOMs generated. |
| Final current-tree privacy/secret and security review | Exact-tree security review found no reportable finding; Gitleaks candidates were synthetic. Current-tree, reachable-history, ref, screenshot, and artifact privacy scans passed after the authorized narrow content rewrite. |

Tests run on the local toolchain do not by themselves prove support on every platform or constitute
production certification. See [compatibility](../releases/compatibility.md).
