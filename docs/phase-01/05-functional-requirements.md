# Functional requirements register

Each requirement is intended to be independently verifiable in a future implementation.

## Identity and tenancy

- **FR-001** The system MUST allow a user to register with validated credentials.
- **FR-002** The system MUST authenticate a registered user through an opaque server-side session represented in the browser by a Secure, HttpOnly cookie containing a cryptographically random session credential; browser JWTs MUST NOT be the default V1 authentication design.
- **FR-003** The system MUST allow an authenticated user to log out and invalidate the associated opaque server-side session.
- **FR-004** The system MUST allow an authenticated user to change their password after current-credential verification.
- **FR-005** The system MUST provide a time-bounded password-reset flow that does not reveal whether an account exists.
- **FR-006** The system MUST support configurable optional email verification for self-hosted deployments.
- **FR-007** The system MUST allow an authenticated user to create an organization and become its initial Owner.
- **FR-008** The system MUST allow authorized users to update organization settings.
- **FR-009** The system MUST allow Owners and Admins to create a time-bounded, lifecycle-controlled organization invitation token/link without SMTP; when email is configured, the system MAY deliver the same invitation flow by email.
- **FR-010** The system MUST allow Owners and Admins to remove organization members, except that the final Owner cannot be removed.
- **FR-011** The system MUST allow Owners and Admins to change non-owner member roles within the permissions matrix.
- **FR-012** The system MUST enforce organization-scoped RBAC and reject unauthorized cross-tenant access.

## Applications and keys

- **FR-013** The system MUST allow authorized users to create, update, and archive an application.
- **FR-014** The system MUST allow each application to have development, staging, and production environments.
- **FR-015** The system MUST allow authorized users to create an application API key for an application environment.
- **FR-016** The system MUST display a newly created application API key only once and store only a non-reversible verification representation thereafter.
- **FR-017** The system MUST associate every application API key with a non-secret prefix and last-used timestamp.
- **FR-018** The system MUST allow authorized users to revoke and rotate an application API key.
- **FR-019** The system MUST support an optional expiration time for an application API key and reject an expired key.

## Analysis, detectors, and risk

- **FR-020** The system MUST expose a synchronous, authenticated analyze endpoint for bounded prompt or response content.
- **FR-021** The analysis response MUST return structured findings, severity, risk score, confidence, detector evidence, explanation, and recommended action.
- **FR-022** The v1 detector set MUST identify prompt-injection and instruction-override indicators.
- **FR-023** The v1 detector set MUST identify system-prompt extraction, jailbreak, and role-manipulation indicators.
- **FR-024** The v1 detector set MUST identify suspicious encoded or obfuscated payload indicators.
- **FR-025** The v1 detector set MUST identify secret exposure and PII exposure indicators.
- **FR-026** The v1 detector set MUST identify suspicious URLs, tool-manipulation indicators, and data-exfiltration attempts.
- **FR-027** The system MUST inspect response content for secret and PII leakage.
- **FR-028** The system MUST support redaction of response content when a matching policy requires it, using typed non-reversible placeholders and separate safe finding metadata without retaining original sensitive values solely for future display.
- **FR-029** The risk engine MUST produce an integer score from 0 through 100, one of Low/Medium/High/Critical severity, and confidence.
- **FR-030** The risk engine MUST use a versioned deterministic scoring profile with explicit, testable detector contributions, severity weights, caps, and combination rules; every analysis result MUST identify its scoring-profile version, and no hidden adaptive learning may silently alter enforcement.

## Policies and incidents

- **FR-031** The system MUST allow authorized users to create, edit, enable, and disable organization policies.
- **FR-032** A policy MUST support explicit conditions, ordered priority, and one action: allow, flag, block, redact, or require review.
- **FR-033** The policy engine MUST evaluate enabled matching policies in documented priority order and return the resulting action with rationale.
- **FR-034** The system MUST create an incident manually and automatically when configured policy or severity criteria match.
- **FR-035** An incident MUST record Open, Investigating, Resolved, Ignored, or False Positive status; assignee; comments; timeline; application/environment; findings; and action taken.
- **FR-036** The system MUST allow authorized analysts to assign, comment on, resolve, ignore, and mark incidents false positive.

## Observability and dashboard

- **FR-037** The system MUST record security request/event records according to the applicable privacy storage policy.
- **FR-038** The system MUST support log filtering and search by application, severity, threat type, action, and time range.
- **FR-039** The dashboard MUST present request count, detected threat count, blocked request count, critical incident count, recent incidents, threat distribution, risk distribution, and request volume for an authorized organization.
- **FR-040** The Security Playground MUST accept manually entered prompt or response content and show detailed detector results, risk breakdown, and policy outcome.

## Providers and gateway

- **FR-041** Core analysis, risk, policy, incidents, and logs MUST operate when no AI provider is configured.
- **FR-042** The system MUST allow authorized users to configure an OpenAI-compatible provider with a custom base URL, API key, and model name, including local compatible endpoints such as Ollama only when explicit self-hosted configuration permits them.
- **FR-043** The system MUST label AI-generated incident summaries, attack explanations, mitigation suggestions, policy suggestions, and threat explanations as AI-generated and distinguish them from deterministic findings.
- **FR-044** The gateway MUST support the documented V1 subset of `POST /v1/chat/completions`: non-streaming textual system/user/assistant messages and an allowlist of common generation parameters; it MUST return stable Renzai errors and MUST NOT claim full OpenAI protocol parity.
- **FR-045** The gateway MUST perform input scanning and policy enforcement before provider forwarding and output scanning and policy enforcement before returning provider output.
- **FR-046** The gateway MUST continue deterministic core operation when optional AI intelligence is unavailable; if security inspection cannot produce a valid enforcement decision, it MUST fail closed by default in staging and production while development MAY explicitly opt into a less restrictive behavior; if provider forwarding fails, it MUST return a stable provider/gateway failure response without bypassing security controls.

## Governance, privacy, and platform operations

- **FR-047** The system MUST append audit events for security-sensitive account, membership, key, provider, policy, privacy, retention, and incident actions, including actor, action, resource, timestamp, and metadata.
- **FR-048** Audit events MUST be designed as append-only records; correction MUST create a subsequent event rather than mutate the original event.
- **FR-049** The system MUST support in-app notifications for configured incident or policy events.
- **FR-050** The system MUST support outbound webhook notifications using a signed, timestamped, documented payload contract with replay-handling guidance.
- **FR-051** The system MUST default prompt/response storage to redacted content and allow an application to explicitly select full content, redacted content, or metadata only.
- **FR-052** The system MUST avoid persistence of content for events classified as safe by default, unless an operator explicitly enables safe-content persistence.
- **FR-053** The system MUST default event retention to 30 days and support configurable retention of 7 days, 30 days, 90 days, or a custom duration.
- **FR-054** The system MUST publish OpenAPI documentation for implemented platform endpoints.
- **FR-055** The system MUST expose health and readiness endpoints with documented semantics.
- **FR-056** The system MUST allow authorized operational users to create, enable, disable, and delete organization webhook destinations.
