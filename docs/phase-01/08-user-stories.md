# User story catalog

## Identity, organization, and access

### US-001 — Account creation
As a new user, I want to create an account, so that I can use Renzai.

**Acceptance criteria:** Given valid registration data, when I submit it, then an account is created without exposing sensitive values. Given optional verification is enabled, when I register, then access follows the configured verification policy.

### US-002 — Organization setup
As an authenticated user, I want to create an organization, so that I can isolate my team’s applications.

**Acceptance criteria:** Given I am authenticated, when I create an organization, then I become its Owner and can view it. Given another organization, when I request its data without membership, then access is denied.

### US-003 — Member invitation
As an Owner or Admin, I want to invite a teammate, so that they can collaborate.

**Acceptance criteria:** Given I have invitation permission and no SMTP configuration, when I create an invitation, then a time-bounded, lifecycle-controlled invitation link is available. Given email delivery is configured, when I create an invitation, then the same flow may be delivered by email. Given I lack permission, when I attempt the invitation, then it is denied and audited as appropriate.

### US-004 — Role management
As an Owner, I want to manage roles, so that access matches responsibilities.

**Acceptance criteria:** Given a non-owner member, when I assign a permitted role, then their effective permissions change. Given the final Owner, when removal or demotion is attempted, then it is rejected.

## Applications and integration

### US-005 — Application creation
As a Developer, I want to create an application and environments, so that I can separate development, staging, and production traffic.

**Acceptance criteria:** Given Developer access, when I create an application and environment, then they appear only in my organization. Given Viewer access, when I attempt creation, then it is denied.

### US-006 — API key generation
As a Developer, I want to generate an environment API key, so that my application can authenticate.

**Acceptance criteria:** Given key permission, when I create a key, then its secret is shown once with prefix and metadata. Given I return later, when I view it, then plaintext is unavailable.

### US-007 — Analyze-only integration
As an AI Engineer, I want to submit content to an analysis endpoint, so that I can enforce checks without a provider.

**Acceptance criteria:** Given a valid key and bounded prompt, when I call analysis, then I receive findings, score, severity, confidence, explanation, action, and scoring-profile version. Given no provider configuration, when I call analysis, then deterministic analysis still completes.

### US-008 — Gateway integration
As an AI Engineer, I want to use a gateway compatible with a documented OpenAI-style subset, so that traffic is scanned around provider calls.

**Acceptance criteria:** Given a non-streaming `POST /v1/chat/completions` request containing supported textual messages and generation parameters and a configured provider, when I call the gateway, then input and output are analyzed. Given an input policy block, when I call it, then it is not forwarded. Given streaming or advanced tool/function execution, when I call the V1 gateway, then it is not represented as supported compatibility.

## Detection and policies

### US-009 — Prompt-injection detection
As a Security Analyst, I want prompt-injection indicators detected, so that malicious instruction attempts are visible.

**Acceptance criteria:** Given content matching a documented injection rule, when analyzed, then a structured finding identifies the detector and evidence. Given unchanged deterministic input, when reanalyzed, then the detector outcome is repeatable.

### US-010 — Jailbreak detection
As a Security Analyst, I want jailbreak and role-manipulation indicators detected, so that bypass attempts can be governed.

**Acceptance criteria:** Given a matching jailbreak or role-manipulation payload, when analyzed, then its finding and severity are returned. Given a nonmatching payload, when analyzed, then no unsupported finding is asserted.

### US-011 — Response leakage detection
As an AI Engineer, I want response secret and PII leakage identified, so that unsafe output can be stopped.

**Acceptance criteria:** Given response content matching a configured leakage detector, when analyzed, then a leakage finding is returned. Given a redact policy, when it matches, then returned content uses typed non-reversible placeholders and safe finding metadata; the original sensitive value is not retained solely for later display.

### US-012 — Policy creation
As a Security Analyst, I want to create ordered policies, so that findings lead to consistent actions.

**Acceptance criteria:** Given policy permission, when I save valid conditions, priority, and action, then the policy can be enabled. Given multiple matching policies, when evaluated, then documented priority resolves the outcome.

### US-013 — Blocking
As a Security Analyst, I want to block matching traffic, so that high-risk content is not processed or returned.

**Acceptance criteria:** Given an enabled block policy matches input, when analysis runs, then the result is Block with rationale. Given gateway mode, when the input is blocked, then forwarding does not occur.

### US-014 — Redaction
As a Security Analyst, I want to redact matching output, so that sensitive values are not exposed.

**Acceptance criteria:** Given an enabled redact policy matches output, when it is returned, then configured sensitive portions are replaced and the action is recorded.

## Incident and observability

### US-015 — Incident creation
As a Security Analyst, I want incidents created for important events, so that threats are triaged.

**Acceptance criteria:** Given configured automatic criteria, when a matching event occurs, then an incident includes findings, context, status, and action. Given manual creation permission, when I create one, then it has an auditable timeline entry.

### US-016 — Incident assignment
As a Security Analyst, I want to assign an incident, so that ownership is explicit.

**Acceptance criteria:** Given an open incident and valid organization member, when I assign it, then assignee and timeline update. Given a cross-tenant user, when assignment is attempted, then it is denied.

### US-017 — Incident resolution and false positives
As a Security Analyst, I want to resolve or mark false positives, so that incident state is accurate.

**Acceptance criteria:** Given an incident, when I select Resolved, Ignored, or False Positive with authorization, then status and timeline update. Given False Positive, when it is recorded, then no detector or policy changes silently; later corpus promotion requires explicit human review. Given Developer access, when status change is attempted, then it is denied.

### US-018 — Dashboard
As an authorized user, I want a dashboard, so that I can understand security activity.

**Acceptance criteria:** Given organization events, when I view the dashboard, then requested counts, distributions, volume, and recent incidents reflect accessible data only.

### US-019 — Log filtering
As a Developer, I want to filter logs, so that I can investigate an integration event.

**Acceptance criteria:** Given recorded events, when I filter by supported fields and time range, then only matching organization events are returned.

### US-020 — Security Playground
As a Developer, I want to analyze manual test content, so that I can understand detector and policy behavior.

**Acceptance criteria:** Given playground access, when I submit prompt or response text, then detailed outcomes are shown. Given a selected storage policy, when processing completes, then storage follows it.

## Providers, governance, and resilience

### US-021 — Provider configuration
As an Admin, I want to configure an OpenAI-compatible provider, so that I can enable optional AI assistance.

**Acceptance criteria:** Given valid authorized configuration, when I save it, then secret material is not returned in plaintext. Given a non-HTTPS, private, loopback, metadata-style, credential-bearing, or otherwise unsafe URL, when I save it, then validation rejects it unless an explicit self-hosted local-endpoint exception permits it.

### US-022 — No-provider operation
As an AI Engineer, I want core protection without a provider, so that an outage or privacy choice does not remove safeguards.

**Acceptance criteria:** Given no provider, when deterministic analysis and policy run, then they produce outcomes without AI-generated claims.

### US-023 — Provider failure
As an AI Engineer, I want a clear gateway provider-failure outcome, so that my application handles it safely.

**Acceptance criteria:** Given optional AI intelligence is unavailable, when deterministic analysis runs, then core operation continues. Given security inspection cannot produce a valid decision in staging or production, when gateway processing occurs, then it fails closed by default. Given a configured provider times out, when gateway forwarding occurs, then a stable non-secret provider/gateway failure response is returned without bypassing security controls.

### US-024 — AI incident explanation
As a Security Analyst, I want optional AI explanation, so that I can accelerate triage without confusing it with evidence.

**Acceptance criteria:** Given a provider and request permission, when I request explanation, then it is visibly labelled AI-generated alongside deterministic findings. Given no provider, when requested, then core incident evidence remains available.

### US-025 — Audit trail
As an Owner, I want to review audit events, so that I can investigate sensitive changes.

**Acceptance criteria:** Given a policy, key, membership, or provider change, when it occurs, then an append-only audit event captures actor, action, resource, timestamp, and safe metadata.

### US-026 — Retention and privacy modes
As an Admin, I want retention and storage modes per application, so that privacy controls fit my deployment.

**Acceptance criteria:** Given a newly configured application, when it has no authorized override, then storage defaults to redacted content, retention defaults to 30 days, and safe content is not persisted. Given application settings permission, when I select full, redacted, or metadata-only storage and a supported retention, then subsequent eligible events follow those settings.

### US-027 — Key rotation and revocation
As a Developer, I want to rotate or revoke a key, so that compromised credentials can be contained.

**Acceptance criteria:** Given key permission, when I revoke a key, then it no longer authenticates. Given I rotate it, when the replacement is created, then only the replacement secret is displayed once.

## Additional detection and operations coverage

### US-028 — Encoded or obfuscated payload detection
As a Security Analyst, I want encoded or obfuscated attack indicators detected, so that attempts to evade readable-content checks are visible.

**Acceptance criteria:** Given content matching a documented encoded or obfuscated payload rule, when analyzed, then a structured finding identifies the detector and evidence. Given unchanged deterministic input, when reanalyzed, then the result is repeatable under the same scoring profile.

### US-029 — Advanced threat-indicator detection
As a Security Analyst, I want suspicious URLs, tool-manipulation indicators, and data-exfiltration attempts detected, so that risky external actions and disclosure attempts can be governed.

**Acceptance criteria:** Given content matching a documented suspicious-URL, tool-manipulation, or exfiltration rule, when analyzed, then the applicable structured finding is returned. Given a matching policy, when it evaluates the finding, then the documented action and rationale are returned.

### US-030 — In-app notifications
As a Security Analyst, I want in-app notifications for configured security events, so that I can respond promptly.

**Acceptance criteria:** Given an authorized configured incident or policy event, when it occurs, then an in-app notification is available to the intended authorized recipient. Given an unauthorized user, when they view notifications, then they cannot access another organization’s notification data.

### US-031 — Signed webhook notifications
As an Admin, I want to manage signed webhook destinations, so that external systems can receive trustworthy security notifications.

**Acceptance criteria:** Given operational permission and a destination that passes SSRF policy, when I create and enable it, then eligible events emit signed, timestamped payloads with replay-handling guidance. Given an unsafe destination or missing permission, when I attempt management, then the operation is rejected.

### US-032 — Platform documentation and operational endpoints
As an operator or integration developer, I want endpoint documentation and health/readiness signals, so that I can integrate and operate Renzai predictably.

**Acceptance criteria:** Given an implemented platform endpoint, when I view its published API documentation, then its contract is available. Given a running future deployment, when I request health or readiness, then the documented endpoint semantics distinguish the two operational states.
