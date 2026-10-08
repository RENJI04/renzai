# Renzai v1.0 release-candidate checklist

This checklist prepares Phase 17. It does not authorize a tag, release, package/image publication,
push, or license decision.

## Product

- [ ] Frozen V1 behavior and contracts reconfirmed
- [ ] UI and accessibility evidence current
- [ ] Demo seed/reset, Attack Lab, reference app, and screenshots current

## Testing

- [ ] Backend, frontend, worker, Python SDK, and TypeScript SDK gates pass
- [ ] PostgreSQL, Redis, E2E, and concurrency suites pass
- [ ] Compose startup/migration/session/worker path passes
- [ ] Metrics, traces, exporters, Prometheus, and Grafana pass

## Security and privacy

- [ ] Final security diff and repository scan pass
- [ ] Secrets and personal-data/history scan pass
- [ ] Dependency and container scans reviewed
- [ ] Demo, docs, screenshots, examples, and collections contain synthetic data only

## Documentation

- [ ] Product-first README and Quick Start verified from a clean environment
- [ ] Architecture, security model, threat catalog, claims, limitations, and assurance current
- [ ] OpenAPI, SDK, contribution, FAQ, troubleshooting, and screenshots current
- [ ] All local links and editable Mermaid sources validate

## Phase 17 release decisions

- [ ] License selected and added only with explicit authorization
- [ ] Backend/frontend/SDK/container versions reconciled
- [ ] Changelog finalized
- [ ] Final privacy and Git-history audit completed
- [ ] Release notes, artifacts, checksums, and provenance plan approved
- [ ] GitHub publication, tag, packages, and images receive explicit user approval
