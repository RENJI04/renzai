# CSRF, abuse resistance, and security behavior

The session bootstrap returns a pseudorandom CSRF token deterministically derived from the opaque session credential. The server stores only its session-bound verifier. Cookie-authenticated mutations require `X-Renzai-CSRF` plus exact scheme/host origin or referer validation. Public browser auth mutations validate origin/referer when the browser supplies one; non-browser clients without those headers remain usable.

Login, registration, and reset-request buckets combine operation, normalized identity, and direct peer address, then HMAC the identifier before Redis storage. Redis is fail-closed for these endpoints outside tests. Tests use a bounded in-memory adapter. Login errors deliberately do not reveal whether an account exists, and a dummy Argon2 verification narrows timing differences.

Request logs redact invitation path tokens. Passwords and request bodies are not logged. Opaque secrets never enter audit metadata. Production validation requires HTTPS, secure cookies, and a non-development verifier key. Key IDs on stored credentials allow a future key-ring rotation without changing the credential format.
