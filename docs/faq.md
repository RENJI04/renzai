# Frequently asked questions

## Does Renzai require an AI provider?

No. Detection, risk, policy, incidents, analytics, and enforcement are deterministic. AI
Intelligence is optional advisory assistance.

## Can Renzai run fully self-hosted?

Yes, the repository includes a self-hosted Compose topology. Operators still own TLS, secrets,
backups, capacity, upgrades, public ingress, and production operations.

## Does AI decide whether traffic is blocked?

No. AI output cannot modify deterministic findings, scores, policies, or Gateway decisions.

## Does Renzai support streaming, tools, or multimodal input?

No. The V1 Gateway is deliberately non-streaming and text-only, with no tools/functions or
multimodal contract.

## Does Renzai replace a SIEM, EDR, IDS/IPS, or DLP product?

No. It is an AI-application security and observability control with documented non-claims.

## Can I use local providers?

The provider abstraction supports an explicitly configured OpenAI-compatible local kind, subject to
the exact-host allowlist and outbound policy. Renzai does not discover or trust local endpoints
automatically.

## What data does it store?

Tenant/application metadata, privacy-filtered analysis evidence, deterministic decisions, incidents,
provider-call metadata, audit metadata, and optional advisory AI provenance/results. Application
privacy mode and safe-content settings govern content persistence.

## How are provider keys handled?

Credentials are encrypted with configured purpose-separated key rings and never returned by read
APIs. Application API keys are one-time values stored only as keyed verifiers.

## Which SDKs exist?

Typed Python and TypeScript server-side SDKs exist as local source packages. They are not yet
published to PyPI or npm.

## Is Renzai production certified?

No. Repository assurance and live local-stack verification are not compliance, penetration-test,
availability, or production certification.
