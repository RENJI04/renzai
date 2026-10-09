# Changelog

All notable changes to Renzai are recorded here. The project follows semantic versioning for its
application release. The Python and TypeScript SDKs have independent package versions and are not
yet published.

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
