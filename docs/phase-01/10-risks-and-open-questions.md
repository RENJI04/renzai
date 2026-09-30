# Risks and open questions

## Risk register

| ID | Description | Impact | Likelihood | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| RSK-001 | Detector false positives disrupt valid workflows. | High | High | Tunable rules, evidence, safe rollout, regression corpus. | TBD Security | Open |
| RSK-002 | Detector false negatives permit unsafe traffic. | High | Medium | Layered deterministic rules, policy review, test corpus, transparent limitations. | TBD Security | Open |
| RSK-003 | Sensitive content is retained or logged unexpectedly. | Critical | Medium | Storage modes, redaction, retention tests, data-flow review. | TBD Privacy | Open |
| RSK-004 | Provider or webhook URLs create SSRF paths. | Critical | Medium | URL/DNS/IP validation, allowlists, timeouts, redirect controls. | TBD Security | Open |
| RSK-005 | Tenant authorization defect exposes data. | Critical | Medium | Server-side checks, isolation tests, audit review. | TBD Engineering | Open |
| RSK-006 | Provider outage disrupts gateway users. | High | Medium | Explicit fail-safe setting, timeout handling, no-provider core. | TBD Engineering | Open |
| RSK-007 | Scope expands into broad security tooling. | High | High | Enforce scope boundaries and change control. | TBD Product | Open |
| RSK-008 | Risk scores are interpreted as certainty. | Medium | High | Explain contributions/confidence; document limitations. | TBD Product | Open |
| RSK-009 | Open-source dependencies introduce vulnerabilities or lifecycle risk. | High | Medium | Dependency policy, scanning in later phases, update process. | TBD Engineering | Open |
| RSK-010 | Gateway protocol compatibility expectations exceed V1 subset. | Medium | Medium | Publish supported subset and compatibility tests. | TBD Product | Open |

## Open-question / decision register

The historical questions are retained below. All have approved V1 decisions.

| ID | Historical question | Approved decision | Decision owner | Status |
|---|---|---|---|---|
| OQ-001 | What auth/session strategy will V1 use? | Dashboard/user auth uses opaque server-side sessions. The browser receives a Secure, HttpOnly cookie containing a cryptographically random session credential; the server retains only appropriate verification representation or session state. CSRF is required for cookie-authenticated state changes. Browser JWTs are not the default. Application integrations use separately scoped application API keys. | Product approved | Resolved |
| OQ-002 | Do self-hosted invitations require email delivery? | SMTP/email is optional. Self-hosted deployments must create a time-bounded invitation token/link without email. Email-configured deployments may deliver the same flow. Invitation tokens must be one-time or otherwise safely lifecycle-controlled. | Product approved | Resolved |
| OQ-003 | What is the default retention period and storage mode? | Default content storage is redacted content; default retention is 30 days. Safe prompt/response content is not persisted by default unless explicitly enabled. Security/audit metadata may be retained under documented policy. | Product approved | Resolved |
| OQ-004 | What is the default gateway fail-open/fail-closed behavior, and may it vary by environment? | Optional AI-intelligence failure does not stop deterministic core operation. If security inspection cannot make a valid decision, staging/production default to fail closed; development may explicitly opt into a less restrictive mode. Provider-forwarding failure returns a stable provider/gateway failure and never bypasses security controls. | Product approved | Resolved |
| OQ-005 | How are risk-score weights calibrated and versioned? | A versioned deterministic scoring profile makes contributions, severity weights, caps, and combination rules explicit and testable. Every result identifies its profile version. Hidden adaptive learning cannot alter enforcement; later calibration uses a version-controlled security regression corpus. | Product approved | Resolved |
| OQ-006 | Which provider URL restrictions and network deployment exceptions are supported? | Remote destinations default to HTTPS. Loopback, RFC1918/private, link-local, multicast, unspecified, and cloud-metadata-style destinations are denied by default. DNS, redirects, and resolved IPs are revalidated. Explicit self-hosted configuration is required for local/private endpoints such as Ollama; URL credentials are forbidden. | Product approved | Resolved |
| OQ-007 | Is full prompt content stored by default? | No. The default is redacted-content storage, subject to safe-content non-persistence and the 30-day default retention policy. | Product approved | Resolved |
| OQ-008 | How do false positives feed future rule configuration without hidden learning? | Marking False Positive does not silently train or modify a detector. Examples may enter a version-controlled regression/calibration corpus only after explicit human review. Rule and policy changes remain explicit and auditable. | Product approved | Resolved |
| OQ-009 | What exact OpenAI-style gateway subset is supported? | V1 targets non-streaming `POST /v1/chat/completions` with textual system/user/assistant messages, an allowlist of common generation parameters, and stable Renzai errors. Streaming and advanced tool/function execution compatibility are deferred; tool-manipulation indicators may still be inspected. Full protocol parity is not claimed. | Product approved | Resolved |
| OQ-010 | What redaction representation preserves enough investigation context? | Use typed, non-reversible placeholders such as `[REDACTED:EMAIL]`, `[REDACTED:PHONE]`, `[REDACTED:API_KEY]`, and `[REDACTED:SECRET]`, plus separate safe finding metadata. Redacted storage must not retain the original sensitive value solely for future display. | Product approved | Resolved |
