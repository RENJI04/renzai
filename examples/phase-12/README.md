# Phase 12 SDK examples

These examples use synthetic content and read credentials from environment variables. Set
`RENZAI_BASE_URL` and `RENZAI_API_KEY` only in a trusted server environment. Never ship an
application API key in a public frontend bundle.

Analyze examples show application-selected content only; they are not middleware that copies every
request body. Gateway examples target only the limited non-streaming text API. Incident and AI
examples require an existing Renzai user session and CSRF token and use a caller-controlled
idempotency key.

Install the local SDK package before running an example. No example disables TLS, logs credentials
or prompt bodies, calls a third-party provider directly, or enables unbounded retries.
