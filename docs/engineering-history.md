# Engineering history

Renzai's current product, development, security, and release guides are the operational source of
truth. The numbered phase documents are preserved in place as an auditable record of how the V1
requirements, architecture, implementation, assurance, deployment, and release evidence evolved.
They are historical evidence rather than a required reading order for using the product.

## Milestones

| Milestone | Preserved evidence | Outcome |
| --- | --- | --- |
| Product definition | [Phase 1](phase-01/01-product-vision.md) | Product boundary, requirements, security expectations, user stories, and acceptance criteria. |
| Architecture and contracts | [Phase 2](phase-02/01-architecture-overview.md) and [Phase 3](phase-03/01-phase-03-intake.md) | Trust boundaries, ADRs, domain model, API contracts, privacy, retention, and error semantics. |
| Product implementation | [Phase 4](phase-04/01-phase-04-scope.md) through [Phase 13](phase-13/01-phase-13-scope.md) | Backend/frontend foundations, identity, deterministic security, policy, providers, incidents, analytics, advisory AI, SDKs, and hardening. |
| Assurance | [Phase 14](phase-14/01-phase-14-scope.md) | Cross-layer test strategy, traceability, integration, E2E, concurrency, and compatibility evidence. |
| Product experience | [Phase 15A](phase-15a/01-phase-15a-scope.md) | Design system, information architecture, responsive workflows, accessibility, and product assets. |
| Deployment and operations | [Phase 15B](phase-15b/01-phase-15b-scope.md) | Compose topology, hardening, observability, CI/security gates, and operational verification. |
| Adoption assets | [Phase 16](phase-16/01-phase-16-scope.md) | Quick Start, synthetic demo, Attack Lab, reference application, API collection, and public documentation. |
| Release assurance | [Phase 17](phase-17/01-phase-17-scope.md) | Freeze, privacy/security audit, clean-clone verification, release artifacts, and v1.0.0 publication plan. |

## Preservation policy

- Keep every Phase 1–17 document and directory intact so historical decisions and evidence retain
  their original context.
- Correct current product guidance in the non-phase documentation instead of rewriting historical
  reports to match later releases.
- Record application maintenance in the [changelog](../CHANGELOG.md) and release notes. SDK package
  versions remain independent of the Renzai application version.
- Treat historical test counts, runtime versions, dates, and release-candidate statements as
  evidence from their recorded point in time, not as claims about the current branch.

The v1.0.0 source release was published on 2026-10-09. See the
[v1.0.0 release notes](releases/v1.0.0.md), current [compatibility evidence](releases/compatibility.md),
and [assurance guide](assurance.md) for the maintained product view.
