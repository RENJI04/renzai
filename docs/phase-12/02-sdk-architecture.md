# SDK architecture

Both SDKs use the same three-layer design:

1. A transport owns only HTTP mechanics: configured base URL, credentials in headers, TLS/runtime
   defaults, timeout, bounded response reading, safe retry policy, and optional metadata-only logs.
2. Protocol parsers validate the public error envelope and critical success fields. Unknown
   additive response fields are ignored for forward compatibility.
3. Public clients serialize language-idiomatic arguments to exact snake_case API fields.

`Renzai` and `AsyncRenzai` (Python), and `Renzai` (TypeScript), accept an application API key and
expose Analyze plus the limited Gateway. `RenzaiSession`/`AsyncRenzaiSession` are intentionally
separate: incidents, analytics, and AI intelligence use an existing user session cookie and CSRF
token under the implemented server contract. No client performs local authorization.

Python uses `httpx` because it is the repository's mature existing HTTP family and supports sync,
async, injected transports, verified TLS, proxy environment conventions, and streaming. TypeScript
uses the runtime's standards-based `fetch`, has zero production dependencies, and permits injected
`fetch` for portability and tests.

The SDKs contact only `base_url`; they contain no provider client, telemetry, external error
reporter, detector, risk calculation, policy evaluator, or hidden security decision.
