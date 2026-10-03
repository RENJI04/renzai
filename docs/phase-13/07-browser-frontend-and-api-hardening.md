# Browser, frontend, and API hardening

The Next.js application now emits a CSP with self-only active resources, `object-src 'none'`,
`frame-ancestors 'none'`, base/form restrictions, and development-only websocket/eval allowances
needed by local HMR. It also emits `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
`X-Frame-Options: DENY`, and a restrictive camera/microphone/geolocation Permissions Policy, while
removing the framework-powered banner. Static assets do not receive blanket `no-store`.

API and Gateway responses retain nosniff/referrer/frame/permissions policy. Sensitive `/api/` and
`/v1/` responses now add `Cache-Control: no-store` plus a non-rendering CSP. HSTS remains conditional
on production HTTPS; local HTTP development is not poisoned. Cookie attributes are environment
specific as documented in the authentication hardening record.

The React source contains no `dangerouslySetInnerHTML`, direct `innerHTML`, or dynamic evaluation.
Incident titles/summaries/comments, AI output, provider names, policy rationale, and finding text use
ordinary React text rendering. Operator comments remain bounded investigation evidence, are not
logged, and are not destructively scrubbed; future integrations must preserve this privacy boundary.

Public errors preserve a request ID but exclude database/provider/encryption internals, content,
credentials, stack traces, and filesystem paths. Structured logging redaction now traverses nested
lists/tuples as well as mappings. Access paths replace control characters, redact bearer path
segments, and cap logged length, preventing line forging and unbounded log fields.

Forwarded headers are not used to authorize Origin or to derive rate-limit identities. A deployment
must terminate them at a configured trusted proxy boundary; Renzai does not attempt to authenticate
an arbitrary internet-supplied `Forwarded`/`X-Forwarded-*` chain.
