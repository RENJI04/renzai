# Changelog

All notable changes to Renzai are recorded here. The project follows semantic versioning for its
application release. The Python and TypeScript SDKs have independent package versions and are not
yet published.

## [1.0.1] — Unreleased

### Security

- Upgrade Next.js from 16.3.8 to 16.4.3 to remediate GHSA-2464-fhr4-w9xw,
  GHSA-673q-mjm6-r5xr, and CVE-2026-94482 while remaining on the supported 16.x line.
- Update the transitive certifi lock from 2026.7.22 to 2026.10.23 to remediate
  GHSA-6q48-6c7w-9gw2 without adding certifi as a direct dependency.
- Refresh compatible transitive Vite and Zod tooling versions to clear retained high-severity
  development-dependency advisories.
- Pin external GitHub Actions to verified immutable revisions and move JavaScript actions to
  Node 24-based releases where available.

### Changed

- Clarify the Python 3.11+ Quick Start/helper boundary and the Python 3.13+ native backend
  development/runtime boundary.
- Add an engineering-history guide while preserving the complete Phase 1–17 evidence in place.
- Group compatible routine Dependabot version updates while keeping security updates separate.
- Run security assurance on pushes to `main` and version tags in addition to pull requests,
  schedules, and manual dispatches.

## [1.0.0] — 2026-10-09

### Added

- Explainable deterministic analysis for eleven documented threat categories, with normalized
  findings, safe evidence, versioned risk scoring, and declarative tenant-scoped policy.
- Analyze API and a limited, fail-closed, non-streaming text Gateway with input/output inspection
  and encrypted provider credentials.
- Organization isolation, application/environment keys, role-aware administration, session and
  CSRF controls, incident investigation, and operational analytics.
- Optional asynchronous advisory AI intelligence, visibly separated from deterministic evidence
  and human decisions.
- Local Python and TypeScript API v1 SDKs; responsive management UI, Security Playground, analyst
  workspace, and accessible product shell.
- Self-hosted Compose stack with gated migrations, PostgreSQL, Redis, Celery, Nginx, metrics,
  Prometheus, OpenTelemetry, Grafana, and operational documentation.
- Synthetic demo seed/reset, Attack Lab, provider-free reference application, Bruno collection,
  screenshots, architecture/security documentation, and assurance tests.

### Security and release preparation

- Tenant/composite database constraints, concurrency tests, privacy-aware retention and telemetry,
  fail-closed enforcement paths, and release privacy/secret/supply-chain review.

The release is not production certification. See [limitations](docs/limitations.md) and
[release notes](docs/releases/v1.0.0.md).
