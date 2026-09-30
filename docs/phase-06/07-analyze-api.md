# Analyze API

`POST /api/v1/analyze` accepts exact JSON fields `direction=input|output`, non-empty `content`, optional bounded `correlation_id`, and optional small string metadata. It authenticates `Authorization: Bearer rz_<env>_<lookup>_<secret>`, derives organization/application/environment/key context from the verifier-only key record, checks expiry/revocation/status/ancestry, and never accepts client-provided tenant scope.

The flow is authenticate → keyed Redis rate limit → UTF-8 byte bound → normalize → required detectors → aggregate/redact → privacy filter → atomic persistence → response. It performs no provider, AI, risk, policy, incident, or gateway work. Limiter failure rejects the request; the Redis key contains only a keyed hash of key identity.

The successful response includes analysis/event IDs, timestamp, direction/source, `safe`, `no_detected_threat`, normalization/ruleset versions, ordered findings, timing, correlation ID, and capability metadata. Risk/action fields are absent. Failures use the stable Renzai envelope including `authentication`, `validation`, `rate_limit`, `inspection_failure`, and `internal_error`; Phase 6 does not emit `policy_block` or `review_required`.

`POST /api/v1/organizations/{org}/playground/analyze` uses the same `AnalysisService` with an authorized session-derived tenant and selected app/environment. No application-key secret is exposed to browser code.
