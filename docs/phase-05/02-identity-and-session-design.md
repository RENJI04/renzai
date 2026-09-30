# Identity and session design

Emails are NFKC-normalized, trimmed, and case-folded for uniqueness while the display value is retained. Passwords must be 12–256 characters with letters and digits and are hashed with Argon2id through `argon2-cffi`; hashes can be upgraded after successful verification.

Sessions use a random 128-bit lookup plus random 256-bit secret. The cookie contains `lookup.secret`; the database stores only lookup, purpose-separated HMAC-SHA-256 verifier, key ID, CSRF verifier, timestamps, and the user's privilege version. Protected environments use `__Host-renzai_session` with Secure, HttpOnly, SameSite=Lax, Path=/ and no Domain. Local development/test uses `renzai_session` without Secure so plain HTTP works; this exception is rejected in staging/production.

Every authenticated request verifies the opaque secret, active user, revocation, idle expiry, absolute expiry, and privilege version, then advances idle expiry without crossing the absolute deadline. Password change revokes every session and returns a new current session. Password reset revokes every session and requires a new login. Logout revokes the current server record and clears the cookie.

Reset (`rzrt_`), verification (`rzvt_`), and invitation (`rziv_`) credentials use distinct HMAC purposes, lookup/verifier storage, expiry, row locks, and single-use timestamps. Development/test responses expose their token as an explicit mail-sink substitute; production responses do not.
