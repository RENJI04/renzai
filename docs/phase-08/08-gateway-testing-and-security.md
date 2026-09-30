# Gateway testing and security

Phase 8 tests cover AES-GCM round trips, nonce uniqueness, wrong context, unknown key IDs, tampering, old-key reads, ciphertext-only persistence, masked APIs, and credential-free audit metadata. The SSRF matrix covers loopback, private IPv4 ranges, link-local, multicast, unspecified, IPv6, IPv4-mapped IPv6, metadata names, mixed public/private DNS answers, unsafe URL syntax, proxy variables, redirects, and explicit local opt-in.

A deterministic in-process HTTP mock provider covers success, health validation, timeout, upstream error, malformed JSON, oversized bodies, redirects, output secrets, sanitized translation, and exactly one attempt. Gateway tests prove input block/review/failure produce zero provider calls and output block/review/redaction/failure never leak unchecked content.

Request tests exercise every supported generation field and reject advanced fields, wrong models, provider ceilings, unsupported seed, invalid bounds, tool roles, multimodal content, too many messages, and oversized text. Persistence tests require separate input/output Gateway events and a provider-call record.

Security review specifically checks credential/log/browser-storage exposure, application-key forwarding, prompt/response logging, SSRF/DNS/redirect/proxy bypass, tenant scope, bounded parsing, retry duplication, and fail-closed behavior. Residual risk includes the normal limits of application-layer SSRF defenses; deployment egress policy remains recommended.

On the 2026-09-28 Windows development host, `scripts/benchmark_phase8.py` ran 2,000 pure-path iterations with median input security 0.2043 ms, mock provider 0.0028 ms, output security 0.1553 ms, provider-excluded local overhead 0.3646 ms, and total 0.3674 ms. This excludes authentication, persistence, Redis, and network I/O and is a local measurement, not an SLA.
