# Phase 2 architecture review

## Status and scope

Phase 2 contains architecture documents and ADRs only. Phase 1 requirements and approved OQ-001–010 decisions remain unchanged. This package is intended to guide Phase 3 data/API contract work; no source, migration, Docker or CI artifact is included.

## Design coverage

| Review item | Architecture location |
|---|---|
| Modular monolith, technology baseline and intake | [01](01-architecture-overview.md), [ADR index](15-architecture-decisions.md) |
| Context, containers, all 19 modules | [02](02-system-context.md)–[04](04-domain-module-architecture.md) |
| Backend, frontend and API boundary catalog | [05](05-backend-architecture.md), [06](06-frontend-architecture.md) |
| Analyze, versioned risk, policy, limited gateway/provider | [07](07-security-engine-architecture.md)–[09](09-gateway-provider-architecture.md) |
| Opaque sessions, API keys, tenancy, privacy, SSRF | [09](09-gateway-provider-architecture.md)–[11](11-data-flow-and-trust-boundaries.md) |
| Events, jobs, outbox, audit and observability | [12](12-runtime-and-background-jobs.md), [13](13-observability-architecture.md) |
| Deployment/trust boundaries/threats | [11](11-data-flow-and-trust-boundaries.md), [14](14-deployment-architecture.md), [16](16-threat-model.md) |
| Phase 1 → Phase 2 → Phase 3 traceability | [17](17-phase-02-traceability.md) |

## Bounded details for Phase 3

The following values/contracts are deliberately not fabricated here: exact API schemas and HTTP status mapping; the gateway generation-parameter allowlist; numerical payload/time/rate limits; session cookie scope, idle/absolute timeout and verifier/key rotation schedules; risk weights and severity thresholds; policy tie precedence and no-match default; `require review` transport behavior; audit retention period; webhook wire signature and replay window; backup objectives; and exact deployment resource sizing. Phase 3 should resolve each against Phase 1 requirements, with product review where a behavior choice would affect users. None reopens OQ-001–010.

## Residual risks

Detectors and redaction can miss novel or obfuscated content. Cross-tenant checks are required in every query and queued job. Outbound URL validation cannot eliminate SSRF without compatible network egress controls. Append-only audit is not cryptographic immutability. Provider downtime makes gateway completions unavailable while local core analysis remains usable. These risks need verification and operational guidance before a V1 release.

## Phase 1 clarification recommendation

Phase 1 lists policy actions and priority but does not fix a universal no-match action, equal-priority tie rule, or exact `require review` gateway response. Phase 3 should record those as bounded product/API decisions before contracts are finalized; Phase 2 has not assumed an implicit allow. Audit retention also needs explicit governance review because prompt-content retention and audit accountability differ.

## Validation record

- All 18 requested Phase 2 documents and 16 sequential ADRs are present. Every ADR has the required status and sections.
- All 14 Mermaid source blocks passed Mermaid 12 syntax parsing with a temporary parser outside the repository. Visual layout was not inspected in a browser.
- Relative Markdown links resolve across the 47 documentation files. The dependency direction and 19 module event contracts were reviewed for cycles; none is proposed.
- [Traceability](17-phase-02-traceability.md) covers FR-001–056, NFR-001–016, SEC-001–025 and US-001–032. The [intake](01-architecture-overview.md) references all ten approved OQ decisions.
- The repository contains only Markdown documentation; no source, migration, Docker, CI, credential or legacy-name artifact was found. Phase 1 documents were preserved; README maturity and links were updated for Phase 2.
- Git is not initialized in this workspace, so there is no branch or working-tree diff to report.
