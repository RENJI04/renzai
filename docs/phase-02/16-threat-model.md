# V1 architecture threat model

Method: lightweight STRIDE review of the [trust boundaries](11-data-flow-and-trust-boundaries.md). Components are proposed, controls are planned, and residual risks remain. `S/T/R/I/D/E` denote spoofing, tampering, repudiation, information disclosure, denial of service and elevation of privilege. Verification is future work.

| Threat (class) | Affected boundary / likely impact | Phase 1 requirement | Architectural mitigation | Residual risk / future verification |
|---|---|---|---|---|
| Account takeover (S/E) | Browser ↔ auth; unauthorized tenant access | FR-002–005; SEC-001,003,024 | Argon2, session verifier, rotation/revocation, reset lifecycle | Stolen credentials remain possible; login/reset abuse tests and session review. |
| Brute force (D/E) | Internet → auth; credential guessing | SEC-003,016 | Per-identity/source rate controls and generic reset response | Distributed guessing; load and enumeration tests. |
| CSRF (T/E) | Browser → API; unauthorized state change | SEC-005 | CSRF proof bound to opaque session, origin controls | Misconfigured proxy/origins; browser integration tests. |
| XSS (T/I) | Untrusted findings → dashboard; session abuse/data leak | SEC-009 | Encode/sanitize rendered content, HttpOnly cookie, CSP planning | UI library misuse; frontend security tests. |
| SQL injection (T/I) | API → PostgreSQL; data compromise | SEC-007–008 | Pydantic bounds, ORM/prepared statements, no string query assembly | Unsafe dynamic filters; query review/fuzzing. |
| Cross-tenant access (I/E) | API/DB/worker/cache; foreign data/action | FR-012; SEC-004 | Derived tenant context, scoped repositories, revalidation in jobs, tenant cache keys | Developer omissions; matrix and cross-tenant integration tests. |
| API key theft (S/E) | Client → API; unauthorized analysis/gateway use | FR-015–019; SEC-002,011,024 | One-time display, non-reversible verifier, scope, expiry/revoke | Client-side compromise; key lifecycle tests and rotation runbook. |
| Session theft (S/E) | Browser/proxy/auth; impersonation | OQ-001; SEC-005,024 | Secure/HttpOnly cookie, verifier-only server store, idle/absolute expiry | Endpoint/browser compromise; cookie/session tests. |
| Provider credential leakage (I) | API/DB/worker → provider; secret exposure | SEC-012,017 | Encryption at rest, restricted decrypt port, log suppression | Key-manager compromise; secret scanning and response/log tests. |
| SSRF / DNS rebinding (I/E) | API/worker → provider/webhook/local network | SEC-020–021 | Shared URL guard, DNS/IP pinning, all-address validation, egress controls | Routing/proxy races; DNS rebinding and IPv4/IPv6 tests. |
| Unsafe redirect (I/E) | Provider/webhook HTTP client → private target | SEC-020–021 | Revalidate each redirect, limit hops, deny URL credentials | Client library behavior; redirect test matrix. |
| Webhook forgery (S/T) | Destination receives fake event | SEC-019 | Signed timestamped payload with rotating secret | Receiver misuse; signature verification examples/tests. |
| Webhook replay (T/R) | Repeated external event | SEC-022 | Event ID, timestamp/freshness and dedupe guidance | Clock skew/receiver storage; replay tests. |
| Prompt/response sensitive leakage (I) | API → logs/DB/provider/telemetry | FR-051–053; SEC-010,023 | Redacted default, safe-content non-persistence, metadata-only option, minimized provider context | Detector misses; privacy regression and data-flow review. |
| Malicious prompt content (T/E) | Client → analysis/gateway/provider | FR-022–026; SEC-007 | Bounded normalization/detectors/risk/policy; no LLM-only authority | False negatives; regression corpus and policy tests. |
| Malicious provider output (T/I) | Provider → gateway/browser | FR-027–028,045; SEC-009–010 | Treat output as untrusted, inspect/redact before return, UI encoding | Novel leaks; output corpus and end-to-end tests. |
| Oversized payload DoS (D) | Internet → proxy/API/detectors/provider | SEC-007,021; NFR-015 | Proxy/API bounds, detector budgets, response ceilings and timeouts | Expensive valid inputs; stress/performance tests. |
| Rate abuse (D) | Internet → analyze/gateway/auth | SEC-003,016 | Shared rate controls with conservative fallback | Distributed sources; load/failure tests. |
| Worker tenant confusion (I/E) | Redis → worker → DB/outbound | SEC-004,023 | Signed/validated job context, re-fetch and tenant-scoped use cases | Stale membership/object state; job isolation tests. |
| Audit tampering (T/R) | API/DB → audit history | FR-047–048; SEC-015 | Append-only API, restricted writes, correction event, backups | DB superuser can alter history; DB permission and restore tests, future tamper evidence. |
| Unsafe operational logs (I) | API/worker → telemetry | NFR-008; SEC-010,017 | Allowlisted structured fields, secret scrubbers, no request bodies | Accidental exception logging; log capture tests. |
| Provider outage (D) | Gateway/AI intelligence → provider | FR-041,046; NFR-002 | Core remains local; stable provider error, bounded timeouts | Gateway completion unavailable; outage integration tests. |
| Policy misconfiguration (T/E) | Admin → policy → enforcement | FR-031–033; SEC-014–015 | Bounded syntax, validation, versioned rollout, audit, deterministic precedence | Authorized error can weaken controls; preview and precedence tests. |
| Invalid inspection (D/E) | Security engine → gateway | FR-046; SEC-014,017 | Staging/production fail closed; explicit dev exception | Availability loss; fault-injection tests. |

The model covers browser, Internet/proxy, API, PostgreSQL, Redis/worker, remote provider, webhook and local-provider exception boundaries. It should be reviewed again when Phase 3 fixes API contracts and data models. No control is claimed to eliminate its threat completely.
