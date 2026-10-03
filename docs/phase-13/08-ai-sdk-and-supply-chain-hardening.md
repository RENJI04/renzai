# AI, SDK, and supply-chain hardening

AI intelligence remains asynchronous, bounded, advisory, and incapable of tool execution or policy
mutation. Incident data is explicitly untrusted context. Per-task strict JSON schemas reject unknown
structures; output is still rendered as text. Worker execution rechecks configuration state and
full-disclosure permission, claims pending work atomically, creates at most one completed result,
performs no uncontrolled retry, and receives only request IDs through the JSON-only Celery task.
Revocation before execution remains a zero-provider-call failure.

Both SDKs now reject empty, oversized, whitespace/control-containing API keys, session tokens, CSRF
tokens, and idempotency keys before their HTTP implementation. Base URLs are capped at 2,048
characters and checked for whitespace/control characters before URL parsing, preventing parser
normalization from hiding an injected authority. Existing no-redirect, TLS-default, no-hidden-
telemetry, bounded response, safe retry, repeated-cursor, and secret-free logging/error behavior is
unchanged. HTTP remains intentionally available for explicit self-hosted development endpoints.

Phase 12 local compatibility passes for Python and TypeScript Analyze, safe Gateway failure, and
incident read. Python wheel and TypeScript tarball inspection found no `.env`, Git data, reports,
test fixtures, credentials, or local filesystem paths. Package lifecycle scripts contain no
consumer `preinstall`, `postinstall`, or `prepare` hooks.

`pip-audit` initially identified vulnerable production `cryptography 46.0.7` plus vulnerable dev
`pytest 8.4.2`. Constraints and the lock now select `cryptography 50.0.2`, `pytest 9.1.1`, and
`pytest-asyncio 1.4.0`; focused tests validate the update, and the resulting Python audit reports no
known vulnerability. `pnpm audit --prod` reports no known vulnerability. Production and development
install paths remain locked (`requirements.lock` and `pnpm-lock.yaml`).

The credential-like pattern scan found only documentation path text and `.env.example`; no real
credential or private key was found. `.gitignore` continues to exclude local `.env`, virtualenvs,
caches, build outputs, coverage, Next output, local databases, and key/certificate artifacts.
