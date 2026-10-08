# Security claims and non-claims

## What Renzai claims

- A deterministic, rule-based V1 security core with eleven documented threat categories.
- Explainable, versioned risk scoring and declarative policy enforcement.
- Durable, tenant-scoped incident investigation linked to original security evidence.
- Privacy-aware storage modes, retention metadata, bounded telemetry, and self-hosted deployment.
- A limited fail-closed text Gateway and direct Analyze API.
- Optional AI-generated incident advice that remains outside enforcement authority.
- Repository test evidence for concurrency, tenant constraints, PostgreSQL, Redis, Compose, and the
  documented local environment.

## What Renzai does not claim

Renzai does not claim perfect jailbreak or prompt-injection prevention, zero false positives or false
negatives, malware sandboxing, EDR, IDS/IPS or SIEM replacement, guaranteed data-loss prevention,
formal compliance certification, penetration-test certification, production SLA, or unhackable
security. Local benchmarks and repository assurance are not production certification.

Security results are one control in an application-specific defense-in-depth design. Operators remain
responsible for identity governance, network policy, TLS, secrets, backup, monitoring, provider risk,
and response procedures.
