# Session and CSRF security

Opaque session credentials are never stored in plaintext. HMAC verification is purpose-separated and constant-time, and stored key IDs preserve a rotation seam. Cookies are HttpOnly, SameSite=Lax, Path=/, and Secure with the `__Host-` prefix outside local development/test.

The bootstrap endpoint returns a session-bound CSRF token whose verifier alone is persisted. State-changing cookie routes require the token and exact same-origin validation. Auth abuse buckets use HMAC-obscured identities in Redis and fail closed if Redis is unavailable outside tests. See [the extended security design](03-csrf-rate-limit-and-security.md).
