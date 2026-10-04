# Backend and integration testing

The deterministic pipeline is covered from validation through normalization, detectors, risk,
policy, and action. Phase 14 adds a full Analyze replay assertion that removes only intentionally
unique entity identifiers/timing and compares every stable decision field, detector result, risk
contribution, profile version, policy winner, and redaction result.

The V1 corpus covers prompt injection, instruction override, system-prompt extraction, jailbreak,
role manipulation, encoded/obfuscated attacks, secret exposure, PII exposure, suspicious URLs,
tool-manipulation indicators, and data-exfiltration indicators. It includes positive, negative,
boundary, Unicode, percent/HTML/Base64 encoding, zero-width, privacy, and false-positive cases.
Production detector semantics were not altered.

Risk tests assert half-up integer arithmetic, contribution ordering, overlap suppression,
corroboration cap, output-secret floor, confidence, score caps, exact 0/100 behavior, immutable
profile metadata, and severity boundaries at 25, 50, and 75. Policy tests cover scope resolution,
priority, inheritance, all/any grammar, all action precedence, redaction targets, version metadata,
and no-match allow.

Analyze tests cover safe/malicious input, action outcomes, privacy modes, metadata, maximum/oversized
input, malformed/revoked/expired/wrong-environment keys, tenant binding, rate limits, commit failure,
and safe envelopes. Gateway tests cover input/provider/output ordering and allow, flag, block, redact,
review, inspection failure, provider error/timeout/configuration, malformed/oversized/framing output,
and redaction failure. Required decisions are persisted before external effects.

The public error serializer has an explicit matrix for all frozen codes and statuses: 401, 403,
404, 409, 422, 429, 500, 502, 503, and 504. Existing public-route tests exercise representative
producers and safe details. No request body, provider body, traceback, secret, or tenant existence is
returned.

Live PostgreSQL selectors cover the full migration schema, composite FKs, uniqueness/partial
indexes, row/advisory locks, automatic incident deduplication, optimistic version conflicts,
retention cascade direction, native date/time analytics, one-in-flight AI work, worker claims, and
result uniqueness. Live Redis covers connectivity, auth/reset/session/Analyze/Gateway limits,
secret-free bounded keys, and actual unavailable-endpoint fail-closed behavior.
