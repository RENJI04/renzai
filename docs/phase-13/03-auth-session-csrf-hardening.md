# Authentication, session, and CSRF hardening

Passwords use an explicit Argon2id v19 profile: 64 MiB memory, three iterations, parallelism four,
32-byte hash, and 16-byte salt. The encoded record preserves these parameters for future rehashing.
Password length and opaque recovery/verification/invitation credentials are bounded. Credential
parsing requires the exact lookup/secret base64url shape before a database or keyed-verifier lookup.

Login now revokes a valid session credential already presented by the browser under a row lock and
then creates a new random session in the same commit. Password change/reset increments the user's
privilege version, revokes sessions, and issues only the contracted replacement. Expired, revoked,
disabled-user, stale-privilege, wrong-verifier, or malformed sessions are rejected and cannot be
revived. Server storage remains lookup plus keyed verifier, never the public credential.

Cookie-authenticated mutations validate a single bounded Origin/Referer, reject parser-invalid
origins, reject cross-site fetch metadata, require one exact 256-bit base64url CSRF value bound to
the session, and use a shared per-session fixed-window limiter. Duplicate/oversized Cookie, CSRF,
Origin, and Referer headers fail safely. Protected deployments use a Secure, HttpOnly, Path `/`,
SameSite=Lax, domainless `__Host-renzai_session`; development uses the explicit non-Secure local
cookie name. CORS accepts only exact HTTP(S) origins and production requires HTTPS.

Auth defaults are five attempts per 15 minutes. Password-reset request/confirmation uses a separate
three-attempts-per-hour limiter. Non-test runtime limiters use Redis and fail closed if Redis cannot
perform the increment. Test runtime uses a deterministic bounded in-memory adapter.

Regression evidence covers session fixation, old-session rejection, exact Argon2 parameters,
malformed/oversized opaque credentials, unknown auth fields, malformed Origin, CSRF/session write
limits, existing reset one-time/session-revocation behavior, and the cross-phase identity suite.

Registration still returns the Phase 3 catalog's conflict response for an existing normalized
email. Changing it would be a public contract change; this is recorded as a low-severity accepted
enumeration limitation rather than silently altered in Phase 13.
