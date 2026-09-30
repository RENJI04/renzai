# Invitations and password reset

Invitation links are time-bounded, target a normalized email and role, work without SMTP, and store only lookup/verifier material. Acceptance requires an authenticated account with the matching normalized email and atomically consumes the token. Reuse, expiry, revocation, mismatch, and foreign identifiers produce the hidden-not-found response.

Password-reset requests always return an accepted response. Existing active accounts receive a 30-minute single-use token; confirmation is row-locked, re-hashes the password, advances privilege version, consumes the token, and revokes all sessions. Development/test returns the token for local verification; production requires delivery integration and never includes it.
