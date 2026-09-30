# Product vision

## Purpose

Renzai is an open-source AI security and observability platform for developers and teams building LLM-powered applications. It will inspect application prompts and responses, then produce explainable findings and policy outcomes. Later releases may also monitor agent and tool activity.

## Product promise

**Secure by default. AI optional. Explainable by design.**

Renzai MUST provide useful core detection and policy decisions without an external LLM. Optional local or remote OpenAI-compatible providers MAY add summaries, explanations, and suggested mitigations, but MUST NOT be the sole authority for security enforcement.

## Intended value

Renzai is intended to let teams integrate deterministic request analysis directly, place an enforcement gateway in front of a provider, investigate security events, and choose privacy-aware retention. It is designed for self-hosting and a modular-monolith implementation path; it is not represented as production-ready in Phase 1.

## Product boundaries

The initial product focuses on LLM application traffic: prompts, responses, their security findings, policies, and associated auditability. It is not a general-purpose security platform or a replacement for endpoint, network, or cloud-security tooling.

## Decision principles

1. Deterministic detectors and policy rules decide the baseline outcome.
2. Every decision SHOULD expose detector evidence and score contributions where safe.
3. Tenant isolation and data-minimizing storage are foundational concerns.
4. Provider unavailability MUST not remove core analysis capability.
5. A future implementation SHOULD favor a modular monolith before distributed services.

## Later-phase architectural principles (not implementation)

The intended initial architecture style is a **modular monolith**. Expected domain boundaries are: auth, users, organizations, memberships, applications, environments, api_keys, security, detectors, risk, policies, incidents, logs, providers, gateway, ai_intelligence, audit, notifications, and analytics. This list defines ownership seams for later architecture work; it does not define services, data models, APIs, or implementation technology.

The security-decision path MUST be designed as:

`Input → normalization → deterministic detectors → heuristics → risk engine → policy engine → optional AI classification/analysis`

It MUST NOT be designed as a prompt sent to an LLM to determine whether it is dangerous. Optional AI is auxiliary evidence and analysis, never the sole decision authority.
