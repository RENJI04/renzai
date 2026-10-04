# Phase 14 scope and baseline

Phase 14 is testing and system assurance for the frozen Renzai V1 implementation. Work started from
clean `main` commit `57a4547b424dc22e9aac8a23c1572ddd69a00e18` (`security: harden Renzai
platform boundaries`). Phase 14 adds tests, test selectors, deterministic local verifiers, coverage
instrumentation, and assurance documentation. It does not add a product capability or migration.

The authoritative behavior remains Phase 1 product requirements, Phase 2 architecture, Phase 3
contracts, and the implementation evidence from Phases 4–13. Tests characterize and enforce that
behavior; they do not reinterpret it.

Out of scope are new detectors, scoring or policy changes, Gateway expansion, streaming, tools,
functions, multimodal requests, agents, AI tasks, notifications, webhooks, SIEM integrations,
deployment automation, and Phase 15 observability/DevOps work. Historical migrations are immutable.

The assurance environment uses synthetic credentials and content, local SQLite for fast API tests,
explicitly disposable PostgreSQL and Redis services for native behavior, deterministic provider
doubles, and ephemeral local HTTP ports. No paid provider or external SaaS is contacted.

The repository still lacks a project license. That remains a Phase 17 release blocker. Registration
enumeration remains the accepted Phase 13 contract limitation and was not changed.
