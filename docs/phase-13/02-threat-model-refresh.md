# Implemented-system threat-model refresh

## Trust boundaries

Traffic crosses browser/SDK to API, API to PostgreSQL/Redis, API or worker to a configured provider,
and API to the Celery broker. Tenant identity is re-established from a live session membership or
application key; caller-supplied organization/resource identifiers are never authority by
themselves. Provider and AI output are hostile data until bounded, parsed, inspected, and enforced.

| Threat actor / event | Representative abuse | Implemented mitigation | Residual risk |
| --- | --- | --- | --- |
| Unauthenticated remote attacker | Credential stuffing, enumeration, malformed/large bodies | Generic login/reset behavior, keyed limits, explicit body/token bounds, production-safe errors | Registration conflict remains contract-visible |
| Authenticated low-privilege user | Call owner/admin mutation | Test-driven five-role backend matrix | A future route must be added to the matrix |
| Malicious tenant | Substitute another tenant's identifiers | Tenant-scoped service queries, hidden responses, composite FKs | PostgreSQL proof requires a reachable live engine |
| Leaked application key | Analyze/Gateway use until revocation | Environment binding, verifier-only storage, expiry/revocation and separate rate limits | Key owner must rotate promptly |
| Malicious analyzed content | ReDoS/decoding expansion/data exfiltration | Byte, candidate, expansion, depth and regex review; deterministic enforcement | Regex detection and PII scrubbing remain best effort |
| Malicious provider | Oversized/malformed/framing-conflicting output | Pinned outbound client, bounded bytes, strict JSON/shape/framing, output inspection | Provider still observes disclosed content by design |
| Malicious AI output | HTML, instructions, schema escape | No tools/actions, strict per-task JSON schema, inert rendering, advisory label | Human reviewers can still trust poor advice |
| Malicious configured URL | SSRF, redirect, proxy bypass, DNS rebinding | Scheme/address validation, all-address check, pinned socket, Host/SNI preservation, no proxy/redirect | Explicit local allowlist is operator trust |
| Compromised browser context | CSRF, clickjacking, stored XSS | Origin plus session-bound CSRF, CSP/frame denial, React text escaping | Same-origin script compromise can act as the user |
| Duplicate/concurrent work | Double owner demotion, duplicate incident/AI execution | Locks, unique/partial indexes, idempotency, optimistic versions | Requires PostgreSQL for authoritative concurrency proof |
| Oversized/malformed input | Memory/CPU or parser abuse | Pre-parse body limits, field/cardinality bounds, bounded provider/SDK responses | Reverse proxy should also enforce limits |
| Malicious SDK input | Header injection, credential redirect, cursor loop | Visible-ASCII bounded secrets, pre-parse URL checks, redirects off, repeated-cursor guard | HTTP self-hosting remains intentionally allowed for development |
| Broker injection | Pickle execution or secret-bearing tasks | JSON-only serializer/content, known task, ID-only arguments, no raw content/credentials | Broker ACL/TLS is deployment responsibility |
| Operator mistake | Debug/docs in production, wildcard local target, weak root | Startup validation rejects unsafe protected-environment settings | External KMS/HSM is not implemented |

The model prioritizes tenant separation, secret confidentiality, deterministic enforcement integrity,
and bounded availability. Failures at inspection, redaction, persistence, provider selection,
credential decryption, rate limiting, or disclosure reauthorization fail closed. Availability is
intentionally sacrificed when a required shared limiter is unavailable.
